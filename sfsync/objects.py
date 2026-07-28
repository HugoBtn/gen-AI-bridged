"""Salesforce objects tracked by the local sync.

The field list of each object mirrors what the existing PoC scripts already
extract (`salesforce_poc_test.py` seeding + `salesforce_lookup.py` queries),
plus the two technical fields every synced object needs:

    Id             — Salesforce record id, used as the local primary key
    SystemModstamp — the watermark the incremental sync filters on. Unlike
                     LastModifiedDate it also moves when Salesforce itself
                     touches a record (roll-up, merge, system update), so it
                     never silently misses a change.

Adding a field here is enough for it to be extracted and stored: the SOQL
SELECT and the local table are both derived from this list.
"""

from dataclasses import dataclass

# Salesforce field used as the incremental watermark.
WATERMARK_FIELD = "SystemModstamp"

# Technical column added to every local table (not a Salesforce field).
SYNCED_AT_COLUMN = "_synced_at"

# Local column types by Salesforce field name; everything else is TEXT
# (dates and datetimes are stored as their ISO-8601 Salesforce strings).
_COLUMN_TYPES = {
    "Amount": "REAL",
    "IsClosed": "INTEGER",
}


def column_type(field):
    """SQL type to use for a Salesforce field."""
    return _COLUMN_TYPES.get(field, "TEXT")


@dataclass(frozen=True)
class ObjectSpec:
    """One tracked Salesforce object and its local table."""

    api_name: str          # Salesforce sObject name, e.g. "Opportunity"
    table: str             # local table name, e.g. "opportunity"
    fields: tuple          # Salesforce fields to extract; "Id" must come first

    def __post_init__(self):
        if self.fields[0] != "Id":
            raise ValueError(f"{self.api_name}: 'Id' must be the first field")
        if WATERMARK_FIELD not in self.fields:
            raise ValueError(f"{self.api_name}: {WATERMARK_FIELD} is required for incremental sync")

    @property
    def select_clause(self):
        return ", ".join(self.fields)


ACCOUNT = ObjectSpec(
    api_name="Account",
    table="account",
    fields=(
        "Id",
        "Name",
        "Industry",
        "Phone",
        "BillingCity",
        "BillingCountry",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
    ),
)

CONTACT = ObjectSpec(
    api_name="Contact",
    table="contact",
    fields=(
        "Id",
        "AccountId",
        "FirstName",
        "LastName",
        "Name",
        "Email",
        "Title",
        "Department",
        "Phone",
        "MobilePhone",
        "MailingCity",
        "MailingCountry",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
    ),
)

OPPORTUNITY = ObjectSpec(
    api_name="Opportunity",
    table="opportunity",
    fields=(
        "Id",
        "AccountId",
        "Name",
        "StageName",
        "Amount",
        "CloseDate",
        "IsClosed",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
    ),
)

TRACKED_OBJECTS = (ACCOUNT, CONTACT, OPPORTUNITY)


def resolve(names):
    """Map Salesforce object names to their spec, preserving TRACKED_OBJECTS order.

    Names are matched case-insensitively so `--objects account,contact` works."""
    if not names:
        return TRACKED_OBJECTS

    wanted = {n.strip().lower() for n in names if n.strip()}
    known = {spec.api_name.lower() for spec in TRACKED_OBJECTS}
    unknown = wanted - known
    if unknown:
        raise ValueError(
            f"Unknown object(s): {', '.join(sorted(unknown))}. "
            f"Tracked objects are: {', '.join(s.api_name for s in TRACKED_OBJECTS)}."
        )
    return tuple(s for s in TRACKED_OBJECTS if s.api_name.lower() in wanted)
