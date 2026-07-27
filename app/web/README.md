# RIKAI · Bridge AI — Web UI

A simple 3-panel interface for the Bridge AI PoC:

- **Left** — data sources (Salesforce connected; Sansan / HR / PM are placeholders).
- **Middle** — search results as person cards; click a card for the full 360° detail.
- **Right** — chat assistant that runs "find somebody" searches against Salesforce.

The chat talks to the Python backend, which runs a **real** Salesforce lookup
(`salesforce_lookup.search_people`) and returns live Contacts and Leads.

## Run it (two terminals)

**1. Backend** (from `gen-AI-bridged/`):

```bash
pip install -r requirements.txt
python app/main.py            # serves http://127.0.0.1:8000
```

**2. Frontend** (from `gen-AI-bridged/app/web/`):

```bash
npm install
npm run dev                   # opens http://localhost:5173
```

The Vite dev server proxies `/api/*` to the backend on port 8000, so no CORS setup
is needed. Open http://localhost:5173 and try the example prompts.

## Example prompts

- `find a Director` · `find a Manager` · `who works in Sales` — search by job title
- `find <name>` — search by contact/lead name
- `find someone at <company>` — search by company / account
- `who is <email>` — search by email

> Searches use a case-insensitive "contains" match, so `find a CTO` also returns
> people whose title contains "cto" as a substring (e.g. Dire**cto**r) — this is the
> underlying `salesforce_lookup` behaviour.

## Build for production

```bash
npm run build                 # outputs to app/web/dist/
```
