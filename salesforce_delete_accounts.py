"""
Salesforce cleanup — delete ALL Accounts (RIKAI x SOLVO Bridge AI PoC)
---------------------------------------------------------------------
Companion to salesforce_poc_test.py. Removes every Account in the org.

Salesforce blocks deleting an Account that still has a Closed Won Opportunity
or an associated Case, so a plain cascade delete fails. This script deletes
the children first (Cases, Opportunities, Contacts) and then the Accounts,
which resets the seeded demo data. Standalone Leads are NOT linked to an
Account and survive — pass --leads to remove those too.

Deletion is DESTRUCTIVE. The script prints how many records it found and
asks for confirmation before deleting. Use --yes to skip the prompt.

    python salesforce_delete_accounts.py                # accounts only (with prompt)
    python salesforce_delete_accounts.py --yes          # accounts, no prompt
    python salesforce_delete_accounts.py --leads --yes  # accounts + leads

Install deps:
    pip install requests
"""

import argparse
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---- CONFIG (same dev org as the seeding script; credentials come from .env) ----
load_dotenv(Path(__file__).resolve().parent / ".env")
MY_DOMAIN = (os.getenv("SFDC_INSTANCE_URL") or "").rstrip("/")
CLIENT_ID = os.getenv("SFDC_CLIENT_ID")
CLIENT_SECRET = os.getenv("SFDC_CLIENT_SECRET")

if not (MY_DOMAIN and CLIENT_ID and CLIENT_SECRET):
    raise SystemExit(
        "Missing Salesforce credentials. Copy .env.example to .env and set "
        "SFDC_INSTANCE_URL, SFDC_CLIENT_ID and SFDC_CLIENT_SECRET."
    )

# The sObject Collections DELETE endpoint accepts at most 200 ids per call.
DELETE_BATCH_SIZE = 200


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


def query_all_ids(instance_url, headers, api_version, sobject):
    """Return every record Id for `sobject`, following query pagination."""
    ids = []
    url = f"{instance_url}/services/data/v{api_version}/query/"
    resp = requests.get(url, headers=headers, params={"q": f"SELECT Id FROM {sobject}"})
    resp.raise_for_status()
    data = resp.json()

    while True:
        ids.extend(r["Id"] for r in data["records"])
        if data.get("done", True):
            break
        # nextRecordsUrl is a path relative to the instance; GET it directly.
        resp = requests.get(f"{instance_url}{data['nextRecordsUrl']}", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return ids


def delete_ids(instance_url, headers, api_version, ids):
    """Delete records in batches via the sObject Collections DELETE endpoint.

    Uses allOrNone=false so one bad record doesn't abort the whole batch.
    Returns (deleted_count, failed_count)."""
    url = f"{instance_url}/services/data/v{api_version}/composite/sobjects"
    deleted = failed = 0

    for start in range(0, len(ids), DELETE_BATCH_SIZE):
        batch = ids[start:start + DELETE_BATCH_SIZE]
        resp = requests.delete(
            url,
            headers=headers,
            params={"ids": ",".join(batch), "allOrNone": "false"},
        )
        if not resp.ok:
            print(f"Batch delete error: {resp.status_code}")
            print(resp.text)
        resp.raise_for_status()

        for result in resp.json():
            if result.get("success"):
                deleted += 1
            else:
                failed += 1
                errs = "; ".join(e.get("message", "") for e in result.get("errors", []))
                print(f"  failed {result.get('id')}: {errs}")

        print(f"  ...{min(start + DELETE_BATCH_SIZE, len(ids))}/{len(ids)} processed")

    return deleted, failed


def purge_sobject(instance_url, headers, api_version, sobject, assume_yes):
    """Query + confirm + delete all records of one sobject type."""
    print(f"Finding all {sobject} records...")
    ids = query_all_ids(instance_url, headers, api_version, sobject)

    if not ids:
        print(f"No {sobject} records to delete.\n")
        return

    print(f"Found {len(ids)} {sobject} record(s).")
    if not assume_yes:
        answer = input(f"Delete ALL {len(ids)} {sobject} records? This cannot be undone. [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print(f"Skipped {sobject}.\n")
            return

    print(f"Deleting {len(ids)} {sobject} record(s)...")
    deleted, failed = delete_ids(instance_url, headers, api_version, ids)
    print(f"Done: {deleted} deleted, {failed} failed.\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Delete ALL Accounts (and optionally Leads) from the Salesforce dev org. "
                    "Deleting an Account cascade-deletes its Contacts, Opportunities and Cases."
    )
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Skip the confirmation prompt (non-interactive).")
    parser.add_argument("--leads", action="store_true",
                        help="Also delete standalone Leads (not linked to any Account).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("Authenticating...")
    token, instance_url = authenticate()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    api_version = get_api_version(instance_url, headers)
    print(f"Using API version v{api_version} on {instance_url}\n")

    # Salesforce refuses to delete an Account while it still has a Closed Won
    # Opportunity or an associated Case, so the naive "delete Account and let it
    # cascade" approach fails. Delete the children explicitly first (Cases and
    # Opportunities, then Contacts), which clears those blockers; the Accounts
    # then delete cleanly.
    for child in ("Case", "Opportunity", "Contact"):
        purge_sobject(instance_url, headers, api_version, child, args.yes)

    purge_sobject(instance_url, headers, api_version, "Account", args.yes)

    if args.leads:
        purge_sobject(instance_url, headers, api_version, "Lead", args.yes)

    print("Cleanup complete.")
