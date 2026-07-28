# Bridge AI Interface – PoC Design for Step 1

This workspace contains a lightweight Proof of Concept design for a multi-system AI bridge interface.

## Goal

Demonstrate that a single natural-language interface can:

- understand a business question,
- select the relevant source system,
- fetch data through connectors,
- combine results into one answer,
- and keep the architecture open for future expansion.

## Intended architecture

- User Interface Layer
  - chat UI / web UI
- AI Orchestration Layer
  - intent parsing
  - tool routing
  - function calling / RAG
  - response synthesis
- Integration & Auth Layer
  - Salesforce connector
  - Sansan connector
  - Internal project connector
  - identity + permission enforcement

## Current repo layout

- `app/main.py`: FastAPI API entry point
- `app/orchestrator.py`: question-to-tool routing and result synthesis
- `app/connectors/`: source-system connector stubs
- `app/config.py`: settings and environment handling
- `salesforce_sync.py`: long-running Salesforce → local-store sync (entry point)
- `sfsync/`: sync package — tracked objects, REST client, storage layer, engine
- `.env.example`: template for credentials and config

## Local Salesforce sync

`salesforce_sync.py` keeps a local SQLite copy of `Account`, `Contact` and
`Opportunity` up to date:

- **cold start** (nothing synced yet) → full extraction, paginated at 2000 rows
  per SOQL response, following `nextRecordsUrl` until exhaustion;
- **afterwards** → hourly poll that only fetches records created or modified
  since the last sync (`WHERE SystemModstamp > <watermark>`), upserted on the
  Salesforce `Id`. Never a second full extraction.

Full vs incremental is decided by the `sync_state` table, not by "is the table
empty": a full extraction interrupted halfway leaves its run marked `running`,
so the next start redoes a full rather than resuming from a watermark that was
never written. Each watermark is rolled back a few minutes (`--safety-margin-minutes`,
default 5) to absorb clock skew and Salesforce indexing latency — upserts are
idempotent, so re-reading a handful of records costs nothing.

```
python salesforce_sync.py                    # run forever, one cycle per hour
python salesforce_sync.py --once             # single cycle, then exit
python salesforce_sync.py --interval 300     # poll every 5 minutes
python salesforce_sync.py --objects Account,Opportunity
python salesforce_sync.py --full --once      # force a full re-extraction
python salesforce_sync.py --status           # sync state per object (no API call)
python salesforce_sync.py --seed             # seed fake demo data, then exit
```

Storage goes through the `Storage` interface in `sfsync/storage.py`; SQLite is
the only implementation today, and every SQL statement lives inside it so another
backend can be added without touching the sync engine. Deletions performed in
Salesforce are out of scope for now (no `IsDeleted` / `queryAll` handling).

## Recommended Phase 1 demo flow

1. User asks a question in natural language.
2. Backend routes the question to one or more connectors.
3. Each connector fetches data from a sandbox system.
4. Orchestrator merges the result.
5. The API returns one consolidated answer with source references.

## Assumptions for this PoC

- Salesforce sandbox is available.
- Sansan sandbox or equivalent API is available.
- Internal project system exposes a simple REST API.
- Permission control is enforced in the source systems, not bypassed by the bridge.

## How to run the code
```
python salesforce_delete_accounts.py --leads --yes
python salesforce_poc_test.py
python salesforce_sync.py
python app/main.py
cd app/web
npm run dev
```