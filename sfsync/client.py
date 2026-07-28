"""Salesforce REST access for the sync process.

Same OAuth 2.0 Client Credentials Flow and same error handling as the existing
PoC scripts (print the Salesforce error body before raising), wrapped in a small
client because a long-running process needs two extra things a one-shot script
doesn't: a session it can refresh when the access token expires, and SOQL
pagination that streams pages instead of buffering the whole result set.
"""

import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Salesforce caps a query response at 2000 rows; anything beyond is reachable
# through `nextRecordsUrl`. We ask for the maximum so a full extraction of N
# records costs ceil(N / 2000) calls instead of ceil(N / 200) at the default.
MAX_BATCH_SIZE = 2000

# Project root (.env lives next to the PoC scripts, one level above this package).
PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_credentials():
    """Read Salesforce credentials from .env, as the other PoC scripts do."""
    load_dotenv(PROJECT_DIR / ".env")
    my_domain = (os.getenv("SFDC_INSTANCE_URL") or "").rstrip("/")
    client_id = os.getenv("SFDC_CLIENT_ID")
    client_secret = os.getenv("SFDC_CLIENT_SECRET")

    if not (my_domain and client_id and client_secret):
        raise SystemExit(
            "Missing Salesforce credentials. Copy .env.example to .env and set "
            "SFDC_INSTANCE_URL, SFDC_CLIENT_ID and SFDC_CLIENT_SECRET."
        )
    return my_domain, client_id, client_secret


class SessionExpired(Exception):
    """Salesforce rejected the access token (expired or invalidated)."""


class SalesforceClient:
    """Authenticated Salesforce REST session with paginated SOQL."""

    def __init__(self, my_domain, client_id, client_secret, timeout=60):
        self.my_domain = my_domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

        self.access_token = None
        self.instance_url = None
        self.api_version = None

    @classmethod
    def from_env(cls, timeout=60):
        return cls(*load_credentials(), timeout=timeout)

    # ---- auth ------------------------------------------------------------

    def authenticate(self):
        """OAuth 2.0 Client Credentials Flow."""
        resp = requests.post(
            f"{self.my_domain}/services/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            print(f"Salesforce auth error: {resp.status_code}")
            print(resp.text)
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.instance_url = data["instance_url"]
        return self.access_token, self.instance_url

    def get_api_version(self):
        """Fetch the latest available REST API version instead of hardcoding it."""
        resp = requests.get(
            f"{self.instance_url}/services/data/",
            headers=self._headers(),
            timeout=self.timeout,
        )
        if not resp.ok:
            print(f"Salesforce error listing API versions: {resp.status_code}")
            print(resp.text)
        resp.raise_for_status()
        versions = resp.json()
        return sorted(versions, key=lambda v: float(v["version"]))[-1]["version"]

    def connect(self):
        """Authenticate and resolve the API version. Safe to call again to refresh."""
        self.authenticate()
        self.api_version = self.get_api_version()
        log.info("Connected to %s (API v%s)", self.instance_url, self.api_version)
        return self

    @property
    def is_connected(self):
        return bool(self.access_token and self.api_version)

    def _headers(self, batch_size=None):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if batch_size:
            headers["Sforce-Query-Options"] = f"batchSize={batch_size}"
        return headers

    def session_headers(self):
        """Headers for callers that talk to Salesforce directly (e.g. the seeder)."""
        return self._headers()

    # ---- requests --------------------------------------------------------

    @staticmethod
    def _is_session_expired(resp):
        """True if a response is Salesforce rejecting an expired/invalid token."""
        if resp.status_code != 401:
            return False
        try:
            body = resp.json()
        except ValueError:
            return True  # 401 with a non-JSON body — treat as an auth failure
        if isinstance(body, list):
            return any(item.get("errorCode") == "INVALID_SESSION_ID" for item in body)
        return True

    def _get(self, url, params=None, batch_size=None, allow_reauth=True):
        """GET with a single transparent re-authentication on an expired token.

        Access tokens outlive a sync cycle but not a process that runs for days,
        so the first call after an expiry must not fail the whole run."""
        resp = requests.get(
            url, headers=self._headers(batch_size), params=params, timeout=self.timeout
        )
        if self._is_session_expired(resp):
            if not allow_reauth:
                raise SessionExpired("Salesforce session expired")
            log.info("Salesforce session expired — re-authenticating")
            self.connect()
            return self._get(url, params=params, batch_size=batch_size, allow_reauth=False)

        if not resp.ok:
            print(f"Salesforce query error: {resp.status_code}")
            print(resp.text)
        resp.raise_for_status()
        return resp

    # ---- SOQL ------------------------------------------------------------

    def query_pages(self, soql):
        """Run a SOQL query and yield each page of records (max 2000 rows).

        Follows `nextRecordsUrl` until the result set is exhausted. Yielding page
        by page keeps a cold-start extraction bounded in memory and lets the
        caller persist as it goes, instead of buffering every record first.

        Note: if the token expires *between* two pages, `_get` re-authenticates
        but the server-side query locator is tied to the old session and the run
        fails. That is recorded as a failed run, so the next cycle simply redoes
        a full extraction — never a silent gap."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/query/"
        data = self._get(url, params={"q": soql}, batch_size=MAX_BATCH_SIZE).json()

        while True:
            yield data["records"]
            if data.get("done", True):
                return
            data = self._get(
                f"{self.instance_url}{data['nextRecordsUrl']}", batch_size=MAX_BATCH_SIZE
            ).json()
