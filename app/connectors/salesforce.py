import os
import sys


def _friendly_error(exc) -> str:
    """Turn a raw connector exception into a short, user-facing message.

    The raw exception (full URLs, stack-y connection-pool text) is useful in the
    server log but terrible in the chat UI, so map the common cases to plain
    language and keep the detail out of the response."""
    import requests

    if isinstance(exc, requests.exceptions.ConnectionError):
        return (
            "Couldn't connect to Salesforce. Check your internet connection and "
            "that SFDC_INSTANCE_URL in .env points to the right org."
        )
    if isinstance(exc, requests.exceptions.Timeout):
        return "Salesforce took too long to respond. Please try again."

    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            body = resp.json()
        except ValueError:
            body = None
        if isinstance(body, list) and body and body[0].get("message"):
            message = body[0]["message"]
            if resp.status_code in (401, 403):
                return f"Salesforce authentication problem: {message}"
            return message
        return f"Salesforce returned an error (HTTP {resp.status_code})."

    return "Something went wrong while querying Salesforce."


class SalesforceConnector:
    """Bridge to the real Salesforce dev org via salesforce_lookup.search_people().

    The heavy lookup module is imported lazily inside the call so the HTTP server
    still starts even if its deps aren't importable yet — any failure then surfaces
    per-request (and is shown gracefully in the UI) instead of at boot."""

    def _search_people(self, **params):
        try:
            from salesforce_lookup import search_people
        except ModuleNotFoundError:
            # salesforce_lookup.py lives at the gen-AI-bridged/ root (parent of app/).
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root not in sys.path:
                sys.path.insert(0, root)
            from salesforce_lookup import search_people
        return search_people(**params)

    def find_people(self, params: dict) -> dict:
        """Run a live person lookup. Returns {people, count, error}."""
        try:
            people = self._search_people(**params)
        except Exception as exc:  # noqa: BLE001 - surface auth/network/query errors to the UI
            # Keep the raw detail in the server log; show a clean message to users.
            print(f"[SalesforceConnector] lookup failed: {exc!r}", file=sys.stderr)
            return {"people": [], "count": 0, "error": _friendly_error(exc)}
        return {"people": people, "count": len(people), "error": None}

    def fetch_demo_data(self) -> dict:
        # Legacy stub kept for backwards compatibility with earlier callers.
        return {
            "answer": "Salesforce trả về thông tin khách hàng, account, và liên hệ liên quan.",
            "records": [
                {"account": "ABC Corp", "owner": "Alice", "stage": "Negotiation"}
            ],
        }
