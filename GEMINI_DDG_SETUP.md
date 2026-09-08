# TruthTrace Gemini + Public Web Setup

## Gemini

1. In `backend/`, create a local `.env` file:

```env
GEMINI_API_KEY=YOUR_REAL_GEMINI_KEY
GEMINI_MODEL=gemini-3.8-flash
```

2. Install the backend AI dependencies:

```bash
cd backend
python -m pip install -r requirements.txt
```

3. Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

The browser never receives `GEMINI_API_KEY`. Gemini is called by FastAPI through:

- `POST /api/cases/{case_id}/gemini-media` — multimodal evidence interpretation
- `POST /api/cases/{case_id}/copilot` — guided case questions
- `POST /api/cases/{case_id}/ai-osint` — Gemini-generated public-web queries followed by the existing DuckDuckGo search layer

If Gemini is unavailable, the Copilot falls back to the deterministic, case-grounded responder.

## DuckDuckGo

The project currently uses its existing DuckDuckGo HTML/Lite public search layer in `backend/app/services/investigation.py`. It is not configured around a secret DuckDuckGo API key, and no fake/unsupported key field has been added.

For exact visual reverse-image retrieval, the existing Web OSINT page keeps the Google Lens upload flow. DuckDuckGo is used for claim/OCR/AI-generated text queries and public-web propagation leads.

## Public propagation wording

TruthTrace labels these results as public/search-indexed investigation leads. It does not claim that a match set represents the entire internet or proves the first-ever appearance.
