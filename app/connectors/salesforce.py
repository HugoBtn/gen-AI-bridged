import os
import sys


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
            return {"people": [], "count": 0, "error": str(exc)}
        return {"people": people, "count": len(people), "error": None}

    def fetch_demo_data(self) -> dict:
        # Legacy stub kept for backwards compatibility with earlier callers.
        return {
            "answer": "Salesforce trả về thông tin khách hàng, account, và liên hệ liên quan.",
            "records": [
                {"account": "ABC Corp", "owner": "Alice", "stage": "Negotiation"}
            ],
        }
