"""Incremental Salesforce -> local-store sync for the RIKAI Bridge AI Interface.

Layers, kept deliberately separate so the storage backend can be swapped later
without touching the sync logic:

    objects.py  — which Salesforce objects/fields are tracked
    client.py   — Salesforce REST access (auth + paginated SOQL)
    storage.py  — Storage interface + SQLite implementation
    engine.py   — full / incremental sync decision, upserts, scheduler loop
"""

from .engine import SyncEngine
from .objects import TRACKED_OBJECTS, ObjectSpec
from .storage import SQLiteStorage, Storage, SyncState

__all__ = [
    "SyncEngine",
    "TRACKED_OBJECTS",
    "ObjectSpec",
    "SQLiteStorage",
    "Storage",
    "SyncState",
]