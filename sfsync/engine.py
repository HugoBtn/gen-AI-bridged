"""Sync engine: decides full vs incremental, extracts, upserts, and schedules.

Per object and per cycle:

    1. read `sync_state` -> full (cold start / interrupted / failed run)
       or incremental (previous run completed and left a watermark)
    2. mark the run as `running` (durably, before any extraction)
    3. page through the SOQL result set, upserting each page
    4. on success store `cycle start - safety margin` as the new watermark

The watermark is the *start* of the extraction, not its end: records modified
while the extraction was running would otherwise fall in the gap between the two
and never be picked up again.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .objects import WATERMARK_FIELD
from .storage import STATUS_SUCCESS

log = logging.getLogger(__name__)

MODE_FULL = "full"
MODE_INCREMENTAL = "incremental"

# Salesforce SOQL datetime literal: UTC, second precision, no quotes.
SOQL_DATETIME = "%Y-%m-%dT%H:%M:%SZ"

DEFAULT_SAFETY_MARGIN_MINUTES = 5
DEFAULT_INTERVAL_SECONDS = 3600


def utcnow():
    return datetime.now(timezone.utc)


def to_soql_datetime(dt):
    return dt.astimezone(timezone.utc).strftime(SOQL_DATETIME)


@dataclass
class ObjectResult:
    """Outcome of one object's sync within a cycle."""

    object_name: str
    mode: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    duration: float = 0.0
    error: str = None

    @property
    def ok(self):
        return self.error is None


@dataclass
class CycleResult:
    number: int
    results: list
    duration: float = 0.0

    @property
    def fetched(self):
        return sum(r.fetched for r in self.results)

    @property
    def inserted(self):
        return sum(r.inserted for r in self.results)

    @property
    def updated(self):
        return sum(r.updated for r in self.results)

    @property
    def failures(self):
        return [r for r in self.results if not r.ok]


class SyncEngine:
    def __init__(self, client, storage, specs,
                 safety_margin_minutes=DEFAULT_SAFETY_MARGIN_MINUTES,
                 force_full=False):
        self.client = client
        self.storage = storage
        self.specs = tuple(specs)
        self.safety_margin = timedelta(minutes=safety_margin_minutes)
        self.force_full = force_full
        self._cycle = 0

        self.storage.initialize(self.specs)

    # ---- mode decision ---------------------------------------------------

    def decide_mode(self, spec):
        """Full unless the previous run completed *and* local data is present.

        Three things independently force a full extraction:
          - no state row at all (cold start)
          - a state row that is not a completed run: an interrupted full leaves
            `running`, a crashed one leaves `failed`; neither watermark is usable
          - an empty local table, even with a `success` state (the DB file was
            wiped or replaced under us)"""
        if self.force_full:
            return MODE_FULL, "forced by --full"

        state = self.storage.get_sync_state(spec.api_name)
        if state is None:
            return MODE_FULL, "no sync state (cold start)"
        if not state.can_run_incremental:
            return MODE_FULL, f"previous run left status={state.status!r}"
        if self.storage.count(spec) == 0:
            return MODE_FULL, "local table is empty"
        return MODE_INCREMENTAL, f"since {state.last_sync_timestamp}"

    def build_soql(self, spec, since=None):
        soql = f"SELECT {spec.select_clause} FROM {spec.api_name}"
        if since:
            # Datetime literals are unquoted in SOQL. `since` is produced by
            # to_soql_datetime(), never by user input.
            soql += f" WHERE {WATERMARK_FIELD} > {since}"
        return soql

    # ---- one object ------------------------------------------------------

    def sync_object(self, spec):
        mode, reason = self.decide_mode(spec)
        state = self.storage.get_sync_state(spec.api_name)
        since = state.last_sync_timestamp if mode == MODE_INCREMENTAL else None

        # Captured before the first API call — see module docstring.
        started_at = utcnow()
        watermark = to_soql_datetime(started_at - self.safety_margin)
        synced_at = to_soql_datetime(started_at)
        started = time.monotonic()

        log.info("%-12s %s (%s)", spec.api_name, mode, reason)
        self.storage.start_run(spec.api_name, mode, to_soql_datetime(started_at))

        result = ObjectResult(object_name=spec.api_name, mode=mode)
        try:
            for page in self.client.query_pages(self.build_soql(spec, since)):
                inserted, updated = self.storage.upsert(spec, page, synced_at)
                result.fetched += len(page)
                result.inserted += inserted
                result.updated += updated
        except Exception as exc:  # network, SOQL, storage — all recoverable next cycle
            result.duration = time.monotonic() - started
            result.error = f"{type(exc).__name__}: {exc}"
            self.storage.fail_run(spec.api_name, result.error, to_soql_datetime(utcnow()))
            log.error("%-12s FAILED after %.1fs — %s", spec.api_name, result.duration, result.error)
            return result

        result.duration = time.monotonic() - started
        # Only now is the watermark trustworthy: every page was persisted.
        self.storage.finish_run(
            spec.api_name, watermark, to_soql_datetime(utcnow()), result.fetched
        )
        log.info(
            "%-12s %s | %d record(s) | %d inserted / %d updated | %.1fs | next watermark %s",
            spec.api_name, mode, result.fetched, result.inserted, result.updated,
            result.duration, watermark,
        )
        return result

    # ---- one cycle -------------------------------------------------------

    def run_cycle(self):
        self._cycle += 1
        started = time.monotonic()
        log.info("--- cycle %d starting ---", self._cycle)

        if not self.client.is_connected:
            self.client.connect()

        results = [self.sync_object(spec) for spec in self.specs]
        cycle = CycleResult(number=self._cycle, results=results,
                            duration=time.monotonic() - started)

        log.info(
            "--- cycle %d done in %.1fs | %d record(s) | %d inserted / %d updated | %d/%d object(s) ok ---",
            cycle.number, cycle.duration, cycle.fetched, cycle.inserted, cycle.updated,
            len(results) - len(cycle.failures), len(results),
        )
        for failure in cycle.failures:
            log.warning("%s will be retried next cycle (%s)", failure.object_name, failure.error)

        # A full extraction is only forced for the first cycle after --full;
        # subsequent cycles resume the normal incremental behaviour.
        self.force_full = False
        return cycle

    # ---- scheduler -------------------------------------------------------

    def run_forever(self, interval=DEFAULT_INTERVAL_SECONDS):
        """Long-running loop. No external cron: the process owns its schedule."""
        log.info("Scheduler started — one cycle every %ds (Ctrl-C to stop)", interval)
        while True:
            try:
                self.run_cycle()
            except Exception as exc:
                # Cycle-level failure (auth, connectivity): keep the process
                # alive and try again at the next tick.
                log.error("Cycle %d aborted: %s: %s", self._cycle, type(exc).__name__, exc)
            log.info("Sleeping %ds until next cycle", interval)
            time.sleep(interval)

    # ---- reporting -------------------------------------------------------

    def status_report(self):
        lines = []
        for spec in self.specs:
            state = self.storage.get_sync_state(spec.api_name)
            rows = self.storage.count(spec)
            if state is None:
                lines.append(f"{spec.api_name:<12} never synced        | {rows:>7} row(s) locally")
                continue
            flag = "" if state.status == STATUS_SUCCESS else "  <- next run will be FULL"
            lines.append(
                f"{spec.api_name:<12} {state.status:<8} {state.mode or '-':<11} | "
                f"{rows:>7} row(s) locally | watermark {state.last_sync_timestamp or '-'}"
                f" | last run {state.last_run_records} record(s){flag}"
            )
            if state.last_error:
                lines.append(f"{'':<12} last error: {state.last_error}")
        return "\n".join(lines)
