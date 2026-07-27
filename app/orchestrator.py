import re

try:
    from app.connectors.salesforce import SalesforceConnector
    from app.connectors.sansan import SansanConnector
    from app.connectors.internal import InternalProjectConnector
except ModuleNotFoundError:
    from connectors.salesforce import SalesforceConnector
    from connectors.sansan import SansanConnector
    from connectors.internal import InternalProjectConnector


# Words that carry no search value in a "find somebody" request; stripped before
# whatever is left is treated as a person's name.
FILLER_WORDS = {
    "find", "search", "for", "look", "lookup", "up", "who", "is", "are", "the",
    "me", "a", "an", "person", "people", "someone", "somebody", "named", "name",
    "call", "called", "get", "show", "give", "please", "in", "on", "of", "any",
    "salesforce", "contact", "contacts", "lead", "leads", "record", "records",
    "work", "works", "working", "everyone", "all", "list",
}

# When the leftover words look like a job title (the seed data gives every person
# a title such as "IT Director — Decision Maker"), search the Title field instead
# of Name — so "find a Director" / "find a CTO" return matches.
TITLE_KEYWORDS = {
    "director", "manager", "cto", "cfo", "ceo", "coo", "vp", "head", "engineer",
    "engineering", "sales", "procurement", "marketing", "president", "owner",
    "champion", "officer", "operations", "product",
}


def parse_query(question: str) -> dict:
    """Light natural-language → search-params heuristic (the "fake bot").

    Extracts email / company / title / phone / name and contacts-only vs
    leads-only intent. Not an LLM — just enough to make the demo feel natural."""
    text = (question or "").strip()
    params: dict = {}

    # email — any address-looking token
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        params["email"] = m.group(0)
        text = text.replace(m.group(0), " ")

    # object-type intent
    low = text.lower()
    if re.search(r"\blead(s)?\b", low):
        params["leads_only"] = True
    if re.search(r"\bcontact(s)?\b", low):
        params["contacts_only"] = True

    # explicit title / role / position
    m = re.search(r"\b(?:title|role|position|job)\s+([A-Za-zÀ-ÿ][\w /-]*)", text, re.IGNORECASE)
    if m:
        params["title"] = m.group(1).strip()
        text = text[:m.start()] + " " + text[m.end():]

    # company after a connector word — take the remainder of the string
    m = re.search(r"\b(?:at|from|company|with|works?\s+at)\s+(.+)$", text, re.IGNORECASE)
    if m:
        params["company"] = m.group(1).strip(" .,;")
        text = text[:m.start()]

    # phone — a run of digits (optionally + and separators)
    m = re.search(r"\+?\d[\d\s.\-]{3,}\d", text)
    if m:
        params["phone"] = m.group(0).strip()
        text = text[:m.start()] + " " + text[m.end():]

    # whatever remains → name, unless it looks like a job title
    tokens = re.findall(r"[A-Za-zÀ-ÿ'\-.]+", text)
    name_tokens = [t for t in tokens if t.lower() not in FILLER_WORDS]
    if name_tokens:
        phrase = " ".join(name_tokens)
        lowered_tokens = {t.lower() for t in name_tokens}
        if "title" not in params and lowered_tokens & TITLE_KEYWORDS:
            params["title"] = phrase
        else:
            params["name"] = phrase

    # both-or-neither: asking for "contacts and leads" means search everything
    if params.get("contacts_only") and params.get("leads_only"):
        params.pop("contacts_only")
        params.pop("leads_only")

    return params


class Orchestrator:
    def __init__(self) -> None:
        self.salesforce = SalesforceConnector()
        self.sansan = SansanConnector()          # placeholder, not wired to UI yet
        self.internal = InternalProjectConnector()  # placeholder, not wired to UI yet

    def handle(self, question: str) -> dict:
        """Route a natural-language question to a live Salesforce person lookup and
        return a UI-ready payload: {question, source, answer, count, people}."""
        params = parse_query(question)

        has_filter = any(params.get(k) for k in ("name", "email", "company", "phone", "title", "id"))
        if not has_filter:
            return {
                "question": question,
                "source": "Salesforce",
                "answer": (
                    "I couldn't tell who to look for. Try “find a Director”, "
                    "“find a Manager”, “find someone at <company>”, or “who is name@example.com”."
                ),
                "count": 0,
                "people": [],
            }

        result = self.salesforce.find_people(params)

        if result.get("error"):
            return {
                "question": question,
                "source": "Salesforce",
                "answer": f"I couldn't reach Salesforce right now: {result['error']}",
                "count": 0,
                "people": [],
                "error": result["error"],
            }

        people = result["people"]
        if not people:
            answer = "No matching person found in Salesforce. Try a shorter or different search term."
        else:
            n_contacts = sum(1 for p in people if p.get("type") == "Contact")
            n_leads = sum(1 for p in people if p.get("type") == "Lead")
            answer = f"Found {n_contacts} contact(s) and {n_leads} lead(s) in Salesforce."

        return {
            "question": question,
            "source": "Salesforce",
            "answer": answer,
            "count": len(people),
            "people": people,
        }
