"""Local storage for the synced Salesforce records.

`Storage` is the interface the sync engine talks to; `SQLiteStorage` is the only
implementation for now. Every SQL statement lives inside the implementation, so
swapping SQLite for Postgres/DuckDB/... later means writing a new subclass, not
touching the engine.

Layout produced by `initialize()`:
    - one table per tracked Salesforce object (columns = extracted fields,
      primary key = Salesforce Id, plus the technical `_synced_at` column)
    - one `sync_state` table holding, per object, the watermark and the outcome
      of the last run — this is what decides full vs incremental.
"""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .objects import SYNCED_AT_COLUMN, WATERMARK_FIELD, column_type

# Values of sync_state.status.
STATUS_RUNNING = "running"   # a run started and has not reported back yet
STATUS_SUCCESS = "success"   # last run completed; watermark is trustworthy
STATUS_FAILED = "failed"     # last run raised; watermark must not be reused

SYNC_STATE_TABLE = "sync_state"

# SQLite has a limit on host parameters per statement (999 on older builds);
# stay well under it when checking which ids already exist.
_ID_CHUNK = 400


@dataclass
class SyncState:
    """Persisted sync bookkeeping for one Salesforce object."""

    object_name: str
    last_sync_timestamp: str = None
    status: str = None
    mode: str = None
    last_run_started_at: str = None
    last_run_finished_at: str = None
    last_run_records: int = 0
    last_error: str = None

    @property
    def can_run_incremental(self):
        """Only a *completed* run leaves a watermark that is safe to resume from.

        A run that was interrupted (status still `running` because the process
        was killed) or that failed never wrote its watermark, so the object goes
        back to a full extraction — an interrupted full must not be mistaken for
        a finished one."""
        return self.status == STATUS_SUCCESS and bool(self.last_sync_timestamp)


class Storage(ABC):
    """Interface between the sync engine and whatever persists the records."""

    @abstractmethod
    def initialize(self, specs):
        """Create the tables for `specs` and the sync-state table if missing."""

    @abstractmethod
    def get_sync_state(self, object_name):
        """Return the SyncState of an object, or None if it was never synced."""

    @abstractmethod
    def all_sync_states(self):
        """Return every persisted SyncState."""

    @abstractmethod
    def start_run(self, object_name, mode, started_at):
        """Mark a run as in progress. Must be durable before extraction starts."""

    @abstractmethod
    def finish_run(self, object_name, watermark, finished_at, records):
        """Mark a run as successful and store its watermark."""

    @abstractmethod
    def fail_run(self, object_name, error, finished_at):
        """Mark a run as failed, leaving the previous watermark untouched."""

    @abstractmethod
    def upsert(self, spec, records, synced_at):
        """Insert or update records by Salesforce Id. Returns (inserted, updated).

        Must be idempotent: re-writing a row that is already up to date is a
        normal consequence of the clock safety margin, not an error."""

    @abstractmethod
    def count(self, spec):
        """Number of locally stored rows for an object."""

    @abstractmethod
    def close(self):
        """Release the underlying resources."""


class SQLiteStorage(Storage):
    """SQLite implementation. One file, one table per object."""

    def __init__(self, path):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        # WAL keeps the DB readable (by the API layer, a notebook, ...) while a
        # sync cycle is writing.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    # ---- schema ----------------------------------------------------------

    def initialize(self, specs):
        with self._conn:
            self._conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {SYNC_STATE_TABLE} (
                    object_name          TEXT PRIMARY KEY,
                    last_sync_timestamp  TEXT,
                    status               TEXT NOT NULL,
                    mode                 TEXT,
                    last_run_started_at  TEXT,
                    last_run_finished_at TEXT,
                    last_run_records     INTEGER NOT NULL DEFAULT 0,
                    last_error           TEXT
                )
                """
            )
            for spec in specs:
                columns = [
                    f'"{f}" {column_type(f)}{" PRIMARY KEY" if f == "Id" else ""}'
                    for f in spec.fields
                ]
                columns.append(f'"{SYNCED_AT_COLUMN}" TEXT NOT NULL')
                self._conn.execute(
                    f'CREATE TABLE IF NOT EXISTS "{spec.table}" ({", ".join(columns)})'
                )
                # The incremental sync and any downstream "what changed?" query
                # both scan on the watermark.
                self._conn.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{spec.table}_modstamp" '
                    f'ON "{spec.table}" ("{WATERMARK_FIELD}")'
                )

    # ---- sync state ------------------------------------------------------

    @staticmethod
    def _to_state(row):
        return SyncState(
            object_name=row["object_name"],
            last_sync_timestamp=row["last_sync_timestamp"],
            status=row["status"],
            mode=row["mode"],
            last_run_started_at=row["last_run_started_at"],
            last_run_finished_at=row["last_run_finished_at"],
            last_run_records=row["last_run_records"],
            last_error=row["last_error"],
        )

    def get_sync_state(self, object_name):
        row = self._conn.execute(
            f"SELECT * FROM {SYNC_STATE_TABLE} WHERE object_name = ?", (object_name,)
        ).fetchone()
        return self._to_state(row) if row else None

    def all_sync_states(self):
        rows = self._conn.execute(
            f"SELECT * FROM {SYNC_STATE_TABLE} ORDER BY object_name"
        ).fetchall()
        return [self._to_state(r) for r in rows]

    def start_run(self, object_name, mode, started_at):
        # Committed immediately: if the process dies mid-extraction, the `running`
        # status survives and the next start knows it must redo a full run.
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO {SYNC_STATE_TABLE}
                    (object_name, status, mode, last_run_started_at, last_run_records, last_error)
                VALUES (?, ?, ?, ?, 0, NULL)
                ON CONFLICT(object_name) DO UPDATE SET
                    status               = excluded.status,
                    mode                 = excluded.mode,
                    last_run_started_at  = excluded.last_run_started_at,
                    last_run_finished_at = NULL,
                    last_run_records     = 0,
                    last_error           = NULL
                """,
                (object_name, STATUS_RUNNING, mode, started_at),
            )

    def finish_run(self, object_name, watermark, finished_at, records):
        with self._conn:
            self._conn.execute(
                f"""
                UPDATE {SYNC_STATE_TABLE}
                   SET status               = ?,
                       last_sync_timestamp  = ?,
                       last_run_finished_at = ?,
                       last_run_records     = ?,
                       last_error           = NULL
                 WHERE object_name = ?
                """,
                (STATUS_SUCCESS, watermark, finished_at, records, object_name),
            )

    def fail_run(self, object_name, error, finished_at):
        with self._conn:
            self._conn.execute(
                f"""
                UPDATE {SYNC_STATE_TABLE}
                   SET status               = ?,
                       last_run_finished_at = ?,
                       last_error           = ?
                 WHERE object_name = ?
                """,
                (STATUS_FAILED, finished_at, str(error)[:2000], object_name),
            )

    # ---- records ---------------------------------------------------------

    @staticmethod
    def _row_values(spec, record, synced_at):
        """Flatten a Salesforce record into the column order of the local table.

        Only the declared fields are read, so the `attributes` block Salesforce
        adds to every record is dropped."""
        return tuple(record.get(f) for f in spec.fields) + (synced_at,)

    def _existing_ids(self, spec, ids):
        found = set()
        for start in range(0, len(ids), _ID_CHUNK):
            chunk = ids[start:start + _ID_CHUNK]
            placeholders = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                f'SELECT "Id" FROM "{spec.table}" WHERE "Id" IN ({placeholders})', chunk
            ).fetchall()
            found.update(r["Id"] for r in rows)
        return found

    def upsert(self, spec, records, synced_at):
        if not records:
            return 0, 0

        columns = list(spec.fields) + [SYNCED_AT_COLUMN]
        rows = [self._row_values(spec, r, synced_at) for r in records]
        ids = [r[0] for r in rows]

        # Counted before writing — afterwards every id exists and the two cases
        # are indistinguishable.
        existing = self._existing_ids(spec, ids)
        updated = sum(1 for i in ids if i in existing)
        inserted = len(ids) - updated

        quoted = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join("?" * len(columns))
        assignments = ", ".join(f'"{c}" = excluded."{c}"' for c in columns if c != "Id")
        sql = (
            f'INSERT INTO "{spec.table}" ({quoted}) VALUES ({placeholders}) '
            f'ON CONFLICT("Id") DO UPDATE SET {assignments}'
        )
        with self._conn:
            self._conn.executemany(sql, rows)

        return inserted, updated

    def count(self, spec):
        row = self._conn.execute(f'SELECT COUNT(*) AS n FROM "{spec.table}"').fetchone()
        return row["n"]

    def close(self):
        self._conn.close()
