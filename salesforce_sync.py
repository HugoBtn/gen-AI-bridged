"""
Salesforce -> local store sync — RIKAI x SOLVO Bridge AI Interface
-------------------------------------------------------------------------------
Long-running process that keeps a local copy of the tracked Salesforce objects
(Account, Contact, Opportunity) up to date:

    - empty / never-synced store  -> full extraction, paginated (2000 rows per
      SOQL response, following nextRecordsUrl until exhaustion)
    - already populated store     -> hourly poll fetching only the records
      created or modified since the last sync (SystemModstamp watermark),
      upserted on the Salesforce Id — never a second full extraction

The decision is driven by the `sync_state` table, not by "is the table empty":
a full extraction interrupted halfway leaves its run marked `running`, so the
next start redoes a full instead of resuming incrementally from a watermark that
was never written.

Usage:
    python salesforce_sync.py                    # run forever, one cycle / hour
    python salesforce_sync.py --once             # single cycle, then exit
    python salesforce_sync.py --interval 300     # poll every 5 minutes
    python salesforce_sync.py --objects Account,Opportunity
    python salesforce_sync.py --full --once      # force a full re-extraction
    python salesforce_sync.py --status           # print sync state and exit
    python salesforce_sync.py --seed             # seed fake demo data, then exit

Install deps:
    pip install -r requirements.txt
"""

import argparse
import logging
import sys

from sfsync import objects
from sfsync.client import SalesforceClient
from sfsync.engine import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_SAFETY_MARGIN_MINUTES,
    SyncEngine,
)
from sfsync.storage import SQLiteStorage

DEFAULT_DB_PATH = "rikai_salesforce.db"

log = logging.getLogger("sfsync")


def configure_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def run_seed(client, args):
    """Seed fake demo data into the org, unchanged from the original PoC script.

    Imported lazily so the sync process itself never needs Faker installed."""
    from salesforce_poc_test import seed_data

    client.connect()
    log.info("Seeding demo data into %s (API v%s)", client.instance_url, client.api_version)
    seed_data(client.instance_url, client.session_headers(), client.api_version, args)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Keep a local store in sync with the Salesforce dev org: full "
                    "extraction on a cold start, hourly incremental poll afterwards.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--db", default=DEFAULT_DB_PATH,
                        help="Path to the local SQLite file")
    parser.add_argument("--objects", default=None,
                        help="Comma-separated Salesforce objects to sync "
                             f"(default: {', '.join(s.api_name for s in objects.TRACKED_OBJECTS)})")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS,
                        help="Seconds between two sync cycles")
    parser.add_argument("--safety-margin-minutes", type=int, default=DEFAULT_SAFETY_MARGIN_MINUTES,
                        help="Minutes subtracted from each watermark to absorb clock skew "
                             "and Salesforce indexing latency (upserts are idempotent, so "
                             "re-reading a few records costs nothing)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single cycle and exit instead of looping")
    parser.add_argument("--full", action="store_true",
                        help="Force a full extraction on the next cycle, ignoring watermarks")
    parser.add_argument("--status", action="store_true",
                        help="Print the sync state of each object and exit (no API call)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    seed = parser.add_argument_group(
        "seeding", "Populate the org with fake demo data (does not sync anything)"
    )
    seed.add_argument("--seed", action="store_true",
                      help="Seed fake demo data into the org, then exit")
    seed.add_argument("--accounts", type=int, default=15,
                      help="Number of Accounts to create")
    seed.add_argument("--contacts-per-account", type=int, default=4,
                      help="Max contacts per account; actual count is random 1..N")
    seed.add_argument("--leads", type=int, default=10,
                      help="Number of unqualified Leads to create")
    seed.add_argument("--cases", type=int, default=8,
                      help="Number of support Cases to create")

    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.verbose)

    try:
        specs = objects.resolve(args.objects.split(",") if args.objects else None)
    except ValueError as exc:
        raise SystemExit(str(exc))

    if args.seed:
        run_seed(SalesforceClient.from_env(), args)
        return

    storage = SQLiteStorage(args.db)
    try:
        if args.status:
            # Report-only: build the engine (which creates the schema if needed)
            # without a Salesforce session.
            engine = SyncEngine(client=None, storage=storage, specs=specs)
            print(f"Local store: {args.db}\n")
            print(engine.status_report())
            return

        client = SalesforceClient.from_env()
        engine = SyncEngine(
            client=client,
            storage=storage,
            specs=specs,
            safety_margin_minutes=args.safety_margin_minutes,
            force_full=args.full,
        )
        log.info("Local store: %s | objects: %s",
                 args.db, ", ".join(s.api_name for s in specs))

        if args.once:
            cycle = engine.run_cycle()
            if cycle.failures:
                raise SystemExit(1)
        else:
            engine.run_forever(interval=args.interval)
    except KeyboardInterrupt:
        log.info("Interrupted — stopping after the current cycle state was saved.")
    finally:
        storage.close()


if __name__ == "__main__":
    main()
