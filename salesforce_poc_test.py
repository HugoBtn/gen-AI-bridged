"""
Salesforce API feasibility test — RIKAI x SOLVO Bridge AI Interface PoC
----------------------------------------------------------------------
1. Authenticates via OAuth 2.0 Client Credentials Flow
2. Seeds realistic, diverse demo data:
     - Accounts    → real French companies (public open-data API, no key needed)
     - Contacts    → 1..N per account with B2B buying-role titles
     - Opportunities → sector-scaled amounts, weighted stages, spread close dates
     - Leads       → unqualified prospects, not yet linked to an Account
     - Cases       → support tickets on existing Accounts, varied Status/Priority
3. Runs cross-object SOQL queries (simulates "Bridge AI" aggregations)

Volumes are configurable via argparse so you can regenerate different demo sizes:
    python salesforce_poc_test.py --accounts 30 --contacts-per-account 4 --leads 20 --cases 12

Install deps:
    pip install requests faker --break-system-packages   (if on a managed system)
    pip install requests faker                            (otherwise)
"""

import argparse
import os
import random
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path

import requests
from dotenv import load_dotenv
from faker import Faker

# ---- CONFIG (credentials come from .env — see .env.example) ----
load_dotenv(Path(__file__).resolve().parent / ".env")
MY_DOMAIN = (os.getenv("SFDC_INSTANCE_URL") or "").rstrip("/")
CLIENT_ID = os.getenv("SFDC_CLIENT_ID")
CLIENT_SECRET = os.getenv("SFDC_CLIENT_SECRET")

if not (MY_DOMAIN and CLIENT_ID and CLIENT_SECRET):
    raise SystemExit(
        "Missing Salesforce credentials. Copy .env.example to .env and set "
        "SFDC_INSTANCE_URL, SFDC_CLIENT_ID and SFDC_CLIENT_SECRET."
    )

fake = Faker()

# Public open-data API (no key required) used to pull real company names.
# We query one keyword per sector so the seeded Accounts span multiple industries.
# Values on the right are exact Salesforce standard Industry picklist entries.
RECHERCHE_ENTREPRISES_URL = "https://recherche-entreprises.api.gouv.fr/search"
SECTOR_KEYWORDS = {
    "technologie": "Technology",
    "finance": "Finance",
    "santé": "Healthcare",
    "retail": "Retail",
    "industrie": "Manufacturing",
    "transport": "Transportation",
}

# The API caps per_page at 25 — any shortfall is topped up with Faker fallbacks.
API_MAX_PER_PAGE = 25

# Deal-size ranges (EUR) by sector: tech/finance skew large, retail small.
SECTOR_AMOUNT_RANGE = {
    "Technology": (50_000, 500_000),
    "Finance": (75_000, 750_000),
    "Healthcare": (30_000, 300_000),
    "Manufacturing": (20_000, 250_000),
    "Transportation": (15_000, 200_000),
    "Retail": (2_000, 40_000),
}
DEFAULT_AMOUNT_RANGE = (5_000, 100_000)

# Weighted stage distribution: many early-funnel deals, few closed ones.
OPP_STAGES = [
    "Prospecting",
    "Qualification",
    "Proposal/Price Quote",
    "Negotiation/Review",
    "Closed Won",
    "Closed Lost",
]
OPP_STAGE_WEIGHTS = [30, 25, 18, 12, 8, 7]

# Realistic B2B buying roles (paired with a functional job title on Contacts/Leads).
BUYER_ROLES = ["Decision Maker", "Influencer", "Technical Buyer", "Champion", "End User"]
JOB_FUNCTIONS = [
    "VP Sales", "Head of Procurement", "IT Director", "CTO", "Operations Manager",
    "CFO", "Product Owner", "Marketing Director", "Head of Engineering", "COO",
]

# Department that goes with each functional job title, so a contact's Department
# is consistent with their Title (e.g. "IT Director" -> Information Technology).
FUNCTION_DEPARTMENT = {
    "VP Sales": "Sales",
    "Head of Procurement": "Procurement",
    "IT Director": "Information Technology",
    "CTO": "Information Technology",
    "Operations Manager": "Operations",
    "CFO": "Finance",
    "Product Owner": "Product",
    "Marketing Director": "Marketing",
    "Head of Engineering": "Engineering",
    "COO": "Executive",
}

# Salesforce's State/Country picklist only accepts exact strings from its own
# controlled list — Faker's fake.country() often doesn't match, so use a fixed
# set of known-valid values instead.
SAFE_COUNTRIES = ["France", "United States", "Vietnam", "Germany",
                  "United Kingdom", "Canada", "Japan", "Australia"]

# Standard Lead picklists (weighted toward the open end of the funnel).
LEAD_STATUSES = ["Open - Not Contacted", "Working - Contacted",
                 "Closed - Converted", "Closed - Not Converted"]
LEAD_STATUS_WEIGHTS = [45, 35, 10, 10]
LEAD_SOURCES = ["Web", "Phone Inquiry", "Partner Referral", "Purchased List", "Other"]

# Standard Case picklists (weighted toward still-open tickets).
CASE_STATUSES = ["New", "Working", "Escalated", "Closed"]
CASE_STATUS_WEIGHTS = [35, 30, 15, 20]
CASE_PRIORITIES = ["Low", "Medium", "High"]
CASE_ORIGINS = ["Phone", "Email", "Web"]
CASE_SUBJECTS = [
    "Login issue on customer portal",
    "Billing discrepancy on latest invoice",
    "Integration API returning 500 errors",
    "Feature request: bulk export",
    "Performance degradation during peak hours",
    "Data sync failure between systems",
    "Request for onboarding assistance",
    "SSO configuration not working",
]


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


def create_record(instance_url, headers, api_version, sobject, payload):
    url = f"{instance_url}/services/data/v{api_version}/sobjects/{sobject}/"
    # Standard duplicate rules (Account/Lead/Contact) would otherwise reject
    # records that fuzzy-match ones seeded on a previous run. These rules allow
    # an override, so we opt in to saving duplicates for this demo-seeding tool.
    post_headers = {**headers, "Sforce-Duplicate-Rule-Header": "allowSave=true"}
    resp = requests.post(url, headers=post_headers, json=payload)
    if not resp.ok:
        print(f"Salesforce error creating {sobject}: {resp.status_code}")
        print(resp.text)
    resp.raise_for_status()
    return resp.json()["id"]


def fetch_real_companies(count):
    """Return `count` company dicts {name, industry, city} sourced from the public
    recherche-entreprises open-data API (no key required), spread across sectors.

    Uses several sector keywords so the industry mix is realistic. Any shortfall
    (API down, not enough results) is topped up with Faker so callers always get
    exactly `count` items and the demo never crashes on a flaky network."""
    per_keyword = min(API_MAX_PER_PAGE, max(1, ceil(count / len(SECTOR_KEYWORDS))))
    companies = []
    seen_names = set()

    for keyword, industry in SECTOR_KEYWORDS.items():
        try:
            resp = requests.get(
                RECHERCHE_ENTREPRISES_URL,
                params={"q": keyword, "per_page": per_keyword},
                timeout=15,
            )
            if not resp.ok:
                print(f"recherche-entreprises error for '{keyword}': {resp.status_code}")
                print(resp.text)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except requests.RequestException as exc:
            print(f"Could not fetch companies for '{keyword}' ({exc}) — using Faker fallback.")
            results = []

        for r in results:
            # Prefer the registered corporate name; fall back to the display name.
            name = r.get("nom_raison_sociale") or r.get("nom_complet")
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            siege = r.get("siege") or {}
            companies.append({
                "name": name[:255],
                "industry": industry,
                "city": siege.get("libelle_commune"),
            })

    # Top up with Faker if the open-data API didn't return enough.
    while len(companies) < count:
        name = fake.company()
        if name in seen_names:
            continue
        seen_names.add(name)
        companies.append({
            "name": name,
            "industry": random.choice(list(SECTOR_KEYWORDS.values())),
            "city": fake.city(),
        })

    random.shuffle(companies)
    return companies[:count]


def make_person_role():
    """Realistic B2B profile: a functional title paired with a buying role, plus a
    department consistent with the function. Returns (title, department)."""
    function = random.choice(JOB_FUNCTIONS)
    role = random.choice(BUYER_ROLES)
    return f"{function} — {role}", FUNCTION_DEPARTMENT[function]


def seed_data(instance_url, headers, api_version, args):
    # Fetch one company pool covering both Accounts and (unqualified) Leads.
    print(f"Fetching {args.accounts + args.leads} real companies from open data...")
    company_pool = fetch_real_companies(args.accounts + args.leads)
    account_companies = company_pool[:args.accounts]
    lead_companies = company_pool[args.accounts:args.accounts + args.leads]

    # ---- Accounts ----
    accounts = []  # list of {"id", "industry"} so opportunities can scale by sector
    print(f"Creating {args.accounts} accounts (real companies)...")
    for company in account_companies:
        acc_id = create_record(instance_url, headers, api_version, "Account", {
            "Name": company["name"],
            "Industry": company["industry"],
            "Phone": fake.phone_number()[:20],
            "BillingCity": company["city"] or fake.city(),
            "BillingCountry": random.choice(SAFE_COUNTRIES),
        })
        accounts.append({"id": acc_id, "industry": company["industry"]})

    account_ids = [a["id"] for a in accounts]

    # ---- Contacts (1..N per account, B2B buying-role titles) ----
    print(f"Creating 1..{args.contacts_per_account} contacts per account...")
    for acc_id in account_ids:
        for _ in range(random.randint(1, args.contacts_per_account)):
            title, department = make_person_role()
            create_record(instance_url, headers, api_version, "Contact", {
                "AccountId": acc_id,
                "FirstName": fake.first_name(),
                "LastName": fake.last_name(),
                "Email": fake.company_email(),
                "Title": title,
                "Department": department,
                "Phone": fake.phone_number()[:20],
                "MobilePhone": fake.phone_number()[:20],
                "MailingCity": fake.city(),
                "MailingCountry": random.choice(SAFE_COUNTRIES),
            })

    # ---- Opportunities (1..3 per account, sector-scaled, weighted stages) ----
    print("Creating 1..3 opportunities per account (sector-scaled amounts)...")
    for acc in accounts:
        low, high = SECTOR_AMOUNT_RANGE.get(acc["industry"], DEFAULT_AMOUNT_RANGE)
        for _ in range(random.randint(1, 3)):
            # Spread close dates across the last 12 months and next 6 months.
            close_date = (datetime.now() + timedelta(days=random.randint(-365, 180))).strftime("%Y-%m-%d")
            create_record(instance_url, headers, api_version, "Opportunity", {
                "AccountId": acc["id"],
                "Name": f"{fake.bs().capitalize()} deal",
                "StageName": random.choices(OPP_STAGES, weights=OPP_STAGE_WEIGHTS, k=1)[0],
                "CloseDate": close_date,
                "Amount": round(random.uniform(low, high), 2),
            })

    # ---- Leads (unqualified prospects, NOT linked to an Account) ----
    print(f"Creating {args.leads} unqualified leads...")
    for company in lead_companies:
        title, _department = make_person_role()  # Leads have no Department field
        create_record(instance_url, headers, api_version, "Lead", {
            "FirstName": fake.first_name(),
            "LastName": fake.last_name(),
            "Company": company["name"],
            "Title": title,
            "Email": fake.company_email(),
            "Phone": fake.phone_number()[:20],
            "MobilePhone": fake.phone_number()[:20],
            "City": fake.city(),
            "Country": random.choice(SAFE_COUNTRIES),
            "Industry": company["industry"],
            "Status": random.choices(LEAD_STATUSES, weights=LEAD_STATUS_WEIGHTS, k=1)[0],
            "LeadSource": random.choice(LEAD_SOURCES),
        })

    # ---- Cases (support tickets on existing Accounts, varied Status/Priority) ----
    if account_ids:
        print(f"Creating {args.cases} support cases on existing accounts...")
        for _ in range(args.cases):
            create_record(instance_url, headers, api_version, "Case", {
                "AccountId": random.choice(account_ids),
                "Subject": random.choice(CASE_SUBJECTS),
                "Status": random.choices(CASE_STATUSES, weights=CASE_STATUS_WEIGHTS, k=1)[0],
                "Priority": random.choice(CASE_PRIORITIES),
                "Origin": random.choice(CASE_ORIGINS),
                "Description": fake.paragraph(nb_sentences=3),
            })
    else:
        print("No accounts created — skipping cases.")

    print("Seeding complete.\n")


def test_query(instance_url, headers, api_version):
    """Simulates the kind of cross-object questions the Bridge AI would answer."""
    # 1. Accounts + open Opportunities + primary Contact (cross-object aggregation).
    #    Phone and Billing City/Country are selected explicitly, otherwise they
    #    can't appear in the printout no matter what was seeded.
    soql = (
        "SELECT Account.Name, Account.Industry, Account.Phone, "
        "Account.BillingCity, Account.BillingCountry, "
        "(SELECT Name, StageName, Amount, CloseDate FROM Opportunities WHERE IsClosed = false), "
        "(SELECT FirstName, LastName, Email, Title FROM Contacts LIMIT 1) "
        "FROM Account ORDER BY Account.Name LIMIT 10"
    )
    url = f"{instance_url}/services/data/v{api_version}/query/"
    resp = requests.get(url, headers=headers, params={"q": soql})
    resp.raise_for_status()
    records = resp.json()["records"]

    print("Sample aggregated result (Account + open Opportunities + primary Contact):\n")
    for r in records:
        opps = r.get("Opportunities", {}).get("records", []) if r.get("Opportunities") else []
        contacts = r.get("Contacts", {}).get("records", []) if r.get("Contacts") else []
        contact_line = (
            f"{contacts[0]['FirstName']} {contacts[0]['LastName']} "
            f"({contacts[0]['Email']}, {contacts[0].get('Title', 'n/a')})"
            if contacts else "no contact"
        )
        location = ", ".join(p for p in (r.get("BillingCity"), r.get("BillingCountry")) if p) or "no location"
        phone = r.get("Phone") or "no phone"
        print(f"- {r['Name']} [{r['Industry']}] — {location} | tel {phone}")
        print(f"    contact: {contact_line}")
        for o in opps:
            # Amount is optional on an Opportunity, so guard against null.
            amount = o.get("Amount")
            amount_str = f"€{amount:,.0f}" if amount is not None else "€ n/a"
            print(f"    open opp: {o['Name']} | {o['StageName']} | {amount_str} | closes {o['CloseDate']}")

    # 2. Lead funnel by status (Bridge AI: "how many unqualified leads per status?").
    lead_soql = "SELECT Status, COUNT(Id) total FROM Lead GROUP BY Status ORDER BY COUNT(Id) DESC"
    resp = requests.get(url, headers=headers, params={"q": lead_soql})
    resp.raise_for_status()
    print("\nLead funnel by status:")
    for r in resp.json()["records"]:
        print(f"    {r['Status']}: {r['total']}")

    # 3. Support cases by priority (Bridge AI: "how many high-priority tickets?").
    case_soql = "SELECT Priority, Status, COUNT(Id) total FROM Case GROUP BY Priority, Status ORDER BY Priority"
    resp = requests.get(url, headers=headers, params={"q": case_soql})
    resp.raise_for_status()
    print("\nSupport cases by priority / status:")
    for r in resp.json()["records"]:
        print(f"    {r.get('Priority', 'n/a')} / {r['Status']}: {r['total']}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed a Salesforce dev org with realistic, diverse demo data "
                    "for the RIKAI x SOLVO Bridge AI Interface PoC."
    )
    parser.add_argument("--accounts", type=int, default=15,
                        help="Number of Accounts to create (default: 15)")
    parser.add_argument("--contacts-per-account", type=int, default=4,
                        help="Max contacts per account; actual count is random 1..N (default: 4)")
    parser.add_argument("--leads", type=int, default=10,
                        help="Number of unqualified Leads to create (default: 10)")
    parser.add_argument("--cases", type=int, default=8,
                        help="Number of support Cases to create (default: 8)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("Authenticating...")
    token, instance_url = authenticate()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    api_version = get_api_version(instance_url, headers)
    print(f"Using API version v{api_version} on {instance_url}\n")

    seed_data(instance_url, headers, api_version, args)
    test_query(instance_url, headers, api_version)
