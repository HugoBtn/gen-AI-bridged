"""
Salesforce lookup — find one person by parameters
-------------------------------------------------------------------------------

A "person" can be either:
    - a Contact (linked to an Account), or
    - a Lead   (standalone, unqualified prospect not yet linked to an Account).

You pass one or more search parameters; they are combined with AND and matched
with a case-insensitive "contains" (SOQL LIKE '%...%'). Provide at least one.

    # by name
    python salesforce_lookup.py --name "Alice Martin"

    # by email fragment
    python salesforce_lookup.py --email martin@

    # narrow: someone named Alice at a company containing "Tech"
    python salesforce_lookup.py --name Alice --company Tech

    # by phone / job title
    python salesforce_lookup.py --phone 0612 --title Director

    # search only Contacts (skip Leads), show up to 5 matches
    python salesforce_lookup.py --name Dupont --contacts-only --limit 5

    # direct fetch by Salesforce record Id (Contact or Lead)
    python salesforce_lookup.py --id 003XXXXXXXXXXXXXXX

    # raw JSON instead of the formatted profile (for piping into other tools)
    python salesforce_lookup.py --email martin@ --json

For each matching Contact the script also pulls their Account, that Account's
Opportunities, and any Cases linked to the Contact — i.e. the kind of
360°-of-a-person view the "Bridge AI" would assemble on demand.

Install deps:
    pip install requests
"""

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import requests
from dotenv import load_dotenv

# ---- CONFIG (same dev org as the seeding / cleanup scripts; creds from .env) ----
load_dotenv(Path(__file__).resolve().parent / ".env")
MY_DOMAIN = (os.getenv("SFDC_INSTANCE_URL") or "").rstrip("/")
CLIENT_ID = os.getenv("SFDC_CLIENT_ID")
CLIENT_SECRET = os.getenv("SFDC_CLIENT_SECRET")

if not (MY_DOMAIN and CLIENT_ID and CLIENT_SECRET):
    raise SystemExit(
        "Missing Salesforce credentials. Copy .env.example to .env and set "
        "SFDC_INSTANCE_URL, SFDC_CLIENT_ID and SFDC_CLIENT_SECRET."
    )


def authenticate():
    """OAuth 2.0 Client Credentials Flow."""
    resp = requests.post(
        f"{MY_DOMAIN}/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data["instance_url"]


def get_api_version(instance_url, headers):
    """Fetch the latest available REST API version instead of hardcoding it."""
    resp = requests.get(f"{instance_url}/services/data/", headers=headers)
    resp.raise_for_status()
    versions = resp.json()
    latest = sorted(versions, key=lambda v: float(v["version"]))[-1]
    return latest["version"]


def run_query(instance_url, headers, api_version, soql):
    """Run a SOQL query and return all records, following pagination."""
    records = []
    url = f"{instance_url}/services/data/v{api_version}/query/"
    resp = requests.get(url, headers=headers, params={"q": soql})
    if not resp.ok:
        print(f"Salesforce query error: {resp.status_code}")
        print(resp.text)
    resp.raise_for_status()
    data = resp.json()

    while True:
        records.extend(data["records"])
        if data.get("done", True):
            break
        resp = requests.get(f"{instance_url}{data['nextRecordsUrl']}", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return records


def soql_escape(value):
    """Escape a value for safe inclusion inside a SOQL string literal.

    Backslash and single-quote are the reserved characters; escaping them
    prevents both broken queries and SOQL injection from user input."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def like_clause(field, value):
    """Case-insensitive 'contains' predicate: field LIKE '%value%'.

    (SOQL LIKE is already case-insensitive for text fields.)"""
    return f"{field} LIKE '%{soql_escape(value)}%'"


def build_conditions(field_map, args):
    """Turn provided --params into a list of SOQL WHERE predicates.

    `field_map` maps each CLI arg name to the object field(s) it searches.
    A param that targets several fields (e.g. phone -> Phone OR MobilePhone)
    becomes one OR-group. All params are later AND-ed together."""
    conditions = []
    for arg_name, fields in field_map.items():
        value = getattr(args, arg_name, None)
        if not value:
            continue
        if arg_name == "name":
            # Match every whitespace-separated token so word order / partials
            # both work: "Martin Alice" and "Alice" both hit "Alice Martin".
            for token in value.split():
                conditions.append(like_clause("Name", token))
        elif len(fields) == 1:
            conditions.append(like_clause(fields[0], value))
        else:
            ors = " OR ".join(like_clause(f, value) for f in fields)
            conditions.append(f"({ors})")
    return conditions


# ---- Contacts -------------------------------------------------------------

CONTACT_FIELDS = (
    "Id, FirstName, LastName, Name, Email, Phone, MobilePhone, Title, "
    "Department, MailingCity, MailingCountry, AccountId, Account.Name, "
    "Account.Industry, Account.Phone, Account.BillingCity, Owner.Name, CreatedDate"
)

# Which Contact field(s) each CLI param searches.
CONTACT_FIELD_MAP = {
    "name": ["Name"],
    "email": ["Email"],
    "company": ["Account.Name"],
    "phone": ["Phone", "MobilePhone"],
    "title": ["Title"],
}


def find_contacts(instance_url, headers, api_version, args):
    if args.id:
        where = f"Id = '{soql_escape(args.id)}'"
    else:
        conditions = build_conditions(CONTACT_FIELD_MAP, args)
        if not conditions:
            return []
        where = " AND ".join(conditions)

    soql = (
        f"SELECT {CONTACT_FIELDS}, "
        "(SELECT Subject, Status, Priority, CreatedDate FROM Cases ORDER BY CreatedDate DESC) "
        f"FROM Contact WHERE {where} ORDER BY Name LIMIT {args.limit}"
    )
    return run_query(instance_url, headers, api_version, soql)


def fetch_opportunities_by_account(instance_url, headers, api_version, account_ids):
    """Fetch the Opportunities of many Accounts in ONE query, grouped by AccountId.

    Querying one account at a time costs an API call per person found (an N+1:
    10 matches = 10 extra calls). A single `AccountId IN (...)` query keeps any
    search at a constant call count, and de-duplicates colleagues who share an
    account for free. With --limit 25 the IN-list stays far below SOQL's
    statement-length cap."""
    ids = sorted({a for a in account_ids if a})
    if not ids:
        return {}

    in_list = ", ".join(f"'{soql_escape(i)}'" for i in ids)
    soql = (
        "SELECT AccountId, Name, StageName, Amount, CloseDate, IsClosed "
        f"FROM Opportunity WHERE AccountId IN ({in_list}) "
        "ORDER BY CloseDate DESC"
    )

    grouped = {}
    for o in run_query(instance_url, headers, api_version, soql):
        grouped.setdefault(o["AccountId"], []).append(o)
    return grouped


# ---- Leads ----------------------------------------------------------------

LEAD_FIELDS = (
    "Id, FirstName, LastName, Name, Email, Phone, MobilePhone, Company, Title, "
    "Industry, Status, LeadSource, IsConverted, City, Country, Owner.Name, CreatedDate"
)

LEAD_FIELD_MAP = {
    "name": ["Name"],
    "email": ["Email"],
    "company": ["Company"],
    "phone": ["Phone", "MobilePhone"],
    "title": ["Title"],
}


def find_leads(instance_url, headers, api_version, args):
    if args.id:
        where = f"Id = '{soql_escape(args.id)}'"
    else:
        conditions = build_conditions(LEAD_FIELD_MAP, args)
        if not conditions:
            return []
        where = " AND ".join(conditions)

    soql = f"SELECT {LEAD_FIELDS} FROM Lead WHERE {where} ORDER BY Name LIMIT {args.limit}"
    return run_query(instance_url, headers, api_version, soql)


# ---- Pretty printing ------------------------------------------------------

def _rel(record, path, default="—"):
    """Safely read a dotted relationship field, e.g. Account.Name."""
    node = record
    for part in path.split("."):
        if not isinstance(node, dict):
            return default
        node = node.get(part)
    return node if node not in (None, "") else default


def print_contact(c, opportunities):
    """Print one contact. `opportunities` is that account's pre-fetched deals."""
    print("=" * 64)
    print(f"CONTACT   {c.get('Name', '—')}    (Id: {c['Id']})")
    print("-" * 64)
    print(f"  Title      : {c.get('Title') or '—'}")
    print(f"  Department : {c.get('Department') or '—'}")
    print(f"  Email      : {c.get('Email') or '—'}")
    print(f"  Phone      : {c.get('Phone') or '—'}   Mobile: {c.get('MobilePhone') or '—'}")
    print(f"  Location   : {c.get('MailingCity') or '—'}, {c.get('MailingCountry') or '—'}")
    print(f"  Owner      : {_rel(c, 'Owner.Name')}")
    print(f"  Created    : {c.get('CreatedDate', '—')}")

    print(f"  Account    : {_rel(c, 'Account.Name')} "
          f"[{_rel(c, 'Account.Industry')}] — {_rel(c, 'Account.BillingCity')}")

    # Account-level opportunities (the deals this person's company is in).
    if c.get("AccountId"):
        if opportunities:
            print(f"  Opportunities on this account ({len(opportunities)}):")
            for o in opportunities:
                amount = f"€{o['Amount']:,.0f}" if o.get("Amount") is not None else "€—"
                flag = "closed" if o.get("IsClosed") else "OPEN"
                print(f"      - {o['Name']} | {o['StageName']} ({flag}) | {amount} | closes {o.get('CloseDate', '—')}")
        else:
            print("  Opportunities on this account: none")

    # Cases linked directly to this contact (from the subquery).
    cases = (c.get("Cases") or {}).get("records", []) if c.get("Cases") else []
    if cases:
        print(f"  Cases linked to this contact ({len(cases)}):")
        for case in cases:
            print(f"      - {case.get('Subject', '—')} | {case.get('Status', '—')} / {case.get('Priority', '—')} | {case.get('CreatedDate', '—')}")
    else:
        print("  Cases linked to this contact: none")
    print()


def print_lead(l):
    print("=" * 64)
    converted = "  (CONVERTED)" if l.get("IsConverted") else ""
    print(f"LEAD      {l.get('Name', '—')}{converted}    (Id: {l['Id']})")
    print("-" * 64)
    print(f"  Company    : {l.get('Company') or '—'}")
    print(f"  Title      : {l.get('Title') or '—'}")
    print(f"  Email      : {l.get('Email') or '—'}")
    print(f"  Phone      : {l.get('Phone') or '—'}   Mobile: {l.get('MobilePhone') or '—'}")
    print(f"  Industry   : {l.get('Industry') or '—'}")
    print(f"  Status     : {l.get('Status') or '—'}   Source: {l.get('LeadSource') or '—'}")
    print(f"  Owner      : {_rel(l, 'Owner.Name')}")
    print(f"  Created    : {l.get('CreatedDate', '—')}")
    print()


# ---- Programmatic API (used by the web backend) ---------------------------

# Cached (instance_url, headers, api_version) so the server doesn't re-auth on
# every request. Lazily initialised on first search_people() call.
_SESSION = None


def _get_session():
    global _SESSION
    if _SESSION is None:
        token, instance_url = authenticate()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        api_version = get_api_version(instance_url, headers)
        _SESSION = (instance_url, headers, api_version)
    return _SESSION


def _invalidate_session():
    """Drop the cached session so the next _get_session() re-authenticates.

    Salesforce access tokens expire (and dev-org sessions time out on
    inactivity); once that happens, requests made with the cached token fail
    with HTTP 401 / INVALID_SESSION_ID and the session must be rebuilt."""
    global _SESSION
    _SESSION = None


def _is_session_expired(exc):
    """True if an HTTPError is Salesforce rejecting an expired/invalid token."""
    resp = getattr(exc, "response", None)
    if resp is None or resp.status_code != 401:
        return False
    try:
        body = resp.json()
    except ValueError:
        return True  # 401 with a non-JSON body — treat as an auth failure
    if isinstance(body, list):
        return any(item.get("errorCode") == "INVALID_SESSION_ID" for item in body)
    return True


def _normalize_contact(c, opps_by_account):
    """Turn a raw Contact record into the unified person shape the UI renders.

    Opportunities come pre-fetched for the whole result set (see
    fetch_opportunities_by_account) so normalizing costs no API call."""
    opportunities = [{
        "name": o.get("Name"),
        "stage": o.get("StageName"),
        "amount": o.get("Amount"),
        "closeDate": o.get("CloseDate"),
        "isClosed": bool(o.get("IsClosed")),
    } for o in opps_by_account.get(c.get("AccountId")) or []]

    raw_cases = (c.get("Cases") or {}).get("records", []) if c.get("Cases") else []
    cases = [{
        "subject": ca.get("Subject"),
        "status": ca.get("Status"),
        "priority": ca.get("Priority"),
        "createdDate": ca.get("CreatedDate"),
    } for ca in raw_cases]

    return {
        "id": c.get("Id"),
        "type": "Contact",
        "name": c.get("Name") or f"{c.get('FirstName') or ''} {c.get('LastName') or ''}".strip(),
        "firstName": c.get("FirstName"),
        "lastName": c.get("LastName"),
        "title": c.get("Title"),
        "department": c.get("Department"),
        "email": c.get("Email"),
        "phone": c.get("Phone"),
        "mobile": c.get("MobilePhone"),
        "city": c.get("MailingCity"),
        "country": c.get("MailingCountry"),
        "company": _rel(c, "Account.Name", default=None),
        "industry": _rel(c, "Account.Industry", default=None),
        "accountCity": _rel(c, "Account.BillingCity", default=None),
        "owner": _rel(c, "Owner.Name", default=None),
        "createdDate": c.get("CreatedDate"),
        "status": None,
        "leadSource": None,
        "isConverted": None,
        "opportunities": opportunities,
        "cases": cases,
    }


def _normalize_lead(l):
    """Turn a raw Lead record into the unified person shape the UI renders."""
    return {
        "id": l.get("Id"),
        "type": "Lead",
        "name": l.get("Name") or f"{l.get('FirstName') or ''} {l.get('LastName') or ''}".strip(),
        "firstName": l.get("FirstName"),
        "lastName": l.get("LastName"),
        "title": l.get("Title"),
        "department": None,
        "email": l.get("Email"),
        "phone": l.get("Phone"),
        "mobile": l.get("MobilePhone"),
        "city": l.get("City"),
        "country": l.get("Country"),
        "company": l.get("Company"),
        "industry": l.get("Industry"),
        "accountCity": None,
        "owner": _rel(l, "Owner.Name", default=None),
        "createdDate": l.get("CreatedDate"),
        "status": l.get("Status"),
        "leadSource": l.get("LeadSource"),
        "isConverted": bool(l.get("IsConverted")),
        "opportunities": [],
        "cases": [],
    }


def search_people(name=None, email=None, company=None, phone=None, title=None,
                  id=None, contacts_only=False, leads_only=False, limit=25):
    """Look up people (Contacts and/or Leads) by parameters and return a list of
    normalized person dicts. Shared by the CLI's callers and the web backend.

    Filters combine with AND and match a case-insensitive 'contains'. Provide at
    least one filter (otherwise returns an empty list)."""
    args = SimpleNamespace(
        name=name, email=email, company=company, phone=phone, title=title,
        id=id, contacts_only=contacts_only, leads_only=leads_only, limit=limit,
    )

    # Retry once on an expired cached token: refresh the session and re-run so a
    # long-lived server doesn't fail the first request after the token times out.
    for attempt in range(2):
        instance_url, headers, api_version = _get_session()
        try:
            contacts = [] if leads_only else find_contacts(instance_url, headers, api_version, args)
            leads = [] if contacts_only else find_leads(instance_url, headers, api_version, args)

            # One extra query for every matched account at once — never one per
            # person. A search costs at most 3 API calls whatever it returns.
            opps_by_account = fetch_opportunities_by_account(
                instance_url, headers, api_version, [c.get("AccountId") for c in contacts]
            )

            people = [_normalize_contact(c, opps_by_account) for c in contacts]
            people += [_normalize_lead(l) for l in leads]
            return people
        except requests.HTTPError as exc:
            if attempt == 0 and _is_session_expired(exc):
                _invalidate_session()
                continue
            raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Look up one person (Contact and/or Lead) in the Salesforce dev "
                    "org by parameters. Filters combine with AND and match a "
                    "case-insensitive 'contains'. Provide at least one filter."
    )
    parser.add_argument("--name", help="Full or partial name (matches any word order).")
    parser.add_argument("--email", help="Full or partial email address.")
    parser.add_argument("--company", help="Company / Account name fragment.")
    parser.add_argument("--phone", help="Phone or mobile fragment.")
    parser.add_argument("--title", help="Job-title fragment (e.g. Director).")
    parser.add_argument("--id", help="Exact Salesforce record Id (Contact or Lead). "
                                     "Overrides the other filters.")

    parser.add_argument("--contacts-only", action="store_true", help="Search Contacts only.")
    parser.add_argument("--leads-only", action="store_true", help="Search Leads only.")

    parser.add_argument("--limit", type=int, default=25,
                        help="Max matches per object type (default: 25).")
    parser.add_argument("--json", action="store_true",
                        help="Print raw JSON records instead of the formatted profile.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.id and not any([args.name, args.email, args.company, args.phone, args.title]):
        print("Provide at least one filter (--name / --email / --company / --phone / --title / --id).")
        sys.exit(1)

    token, instance_url = authenticate()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    api_version = get_api_version(instance_url, headers)

    contacts = [] if args.leads_only else find_contacts(instance_url, headers, api_version, args)
    leads = [] if args.contacts_only else find_leads(instance_url, headers, api_version, args)

    if args.json:
        print(json.dumps({"contacts": contacts, "leads": leads}, indent=2, ensure_ascii=False))
        sys.exit(0)

    total = len(contacts) + len(leads)
    print(f"\nFound {len(contacts)} contact(s) and {len(leads)} lead(s).\n")

    opps_by_account = fetch_opportunities_by_account(
        instance_url, headers, api_version, [c.get("AccountId") for c in contacts]
    )

    for c in contacts:
        print_contact(c, opps_by_account.get(c.get("AccountId")) or [])
    for l in leads:
        print_lead(l)

    if total == 0:
        print("No matching person found. Try a shorter / different fragment.")
