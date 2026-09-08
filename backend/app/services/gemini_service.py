"""Optional Gemini reasoning layer for TruthTrace.

The forensic engine remains the source of detector/forensic signals. Gemini is used
for multimodal interpretation, guided investigation, and query generation.
"""
import json
import os
from pathlib import Path


def _client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured on the server")
    return genai.Client(api_key=key)


def _model():
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def _json_or_text(text):
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.replace("json\n", "", 1).strip()
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None


def analyze_media(file_path: str, claim: str = "", location: str = "", date: str = ""):
    client = _client()
    path = Path(file_path)
    uploaded = client.files.upload(file=str(path))
    prompt = f"""
You are TruthTrace's multimodal forensic investigation assistant.

Analyze the supplied evidence conservatively. Distinguish observations from conclusions.
Never invent facts, URLs, metadata, or provenance. Missing metadata is not proof of manipulation.

Case claim: {claim or 'Not provided'}
Claimed location: {location or 'Not provided'}
Claimed date: {date or 'Not provided'}

Return JSON with these keys:
summary, visible_text, visual_clues, audio_clues, possible_manipulation,
investigation_questions, search_queries, confidence, limitations.
""".strip()
    from google.genai import types
    response = client.models.generate_content(
        model=_model(),
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    parsed = _json_or_text(getattr(response, "text", ""))
    return parsed if parsed is not None else {
        "summary": getattr(response, "text", "") or "No Gemini response returned.",
        "visible_text": [], "visual_clues": [], "audio_clues": [],
        "possible_manipulation": [], "investigation_questions": [],
        "search_queries": [], "confidence": 0, "limitations": ["Gemini returned non-JSON output."]
    }


def answer_case_question(question: str, case_context: dict):
    """Answer a guided copilot question using only server-supplied case facts."""
    client = _client()
    prompt = f"""
You are TruthTrace Context-Aware Investigation Copilot.
Answer the investigator's question using ONLY the supplied TruthTrace case context.
Do not invent facts. Do not create URLs that are not present in the context.
Do not override the forensic engine's verdict. Explain uncertainty where relevant.

INVESTIGATOR QUESTION:
{question}

TRUTHTRACE CASE CONTEXT (server-derived):
{json.dumps(case_context, ensure_ascii=False, default=str)}
""".strip()
    from google.genai import types
    response = client.models.generate_content(
        model=_model(),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return (getattr(response, "text", "") or "No Gemini response returned.").strip()


def generate_search_queries(case_context: dict):
    """Generate a small set of targeted public-web investigation queries."""
    client = _client()
    prompt = f"""
Generate 3 to 5 concise search queries for public-web investigation of this TruthTrace case.
Use only the supplied case facts and OCR text. Prefer exact phrases, distinctive entities,
locations, and claim-specific terms. Do not invent names or facts.
Return JSON only: {{"queries": ["..."]}}

CASE FACTS:
{json.dumps(case_context, ensure_ascii=False, default=str)}
""".strip()
    from google.genai import types
    response = client.models.generate_content(
        model=_model(),
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
    )
    parsed = _json_or_text(getattr(response, "text", "")) or {}
    queries = parsed.get("queries", []) if isinstance(parsed, dict) else []
    return [str(q).strip() for q in queries if str(q).strip()][:5]
