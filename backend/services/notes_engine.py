"""Turn a Whisper transcript into structured sermon notes."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.core.config import LLM_N_CTX
from backend.services.llm import chat_completion

NOTES_SYSTEM_PROMPT = """You are a careful sermon study assistant for a local church.
You only use the transcript you are given. Do not invent quotes, stories, or scripture
references that are not clearly present in the transcript. If a scripture is alluded to
but the reference is not named, say so in the takeaway instead of guessing a verse.

Return ONLY valid JSON with this exact shape:
{
  "main_theme": "one sentence",
  "scriptures": ["Book chapter:verse, or a short quoted allusion if no reference is given"],
  "takeaways": ["short bullet", "short bullet"],
  "summary": "a paragraph of 4-8 sentences"
}

Rules:
- scriptures is an array of strings; use [] if none are mentioned.
- takeaways is 3 to 8 practical bullets.
- Keep the pastor's wording and emphasis. Do not preach a different sermon.
"""

MERGE_SYSTEM_PROMPT = """You merge partial sermon-note JSON objects from sequential
chunks of the SAME sermon into one final JSON object with keys:
main_theme, scriptures, takeaways, summary.

Deduplicate scriptures and takeaways. Keep the overall theme coherent.
Do not add content that does not appear in the partial notes.
Return ONLY valid JSON.
"""

# Rough chars-per-token estimate so a long sermon can be chunked under n_ctx.
_CHARS_PER_TOKEN = 4
_PROMPT_RESERVE_TOKENS = 1200


def _max_chunk_chars() -> int:
    usable = max(LLM_N_CTX - _PROMPT_RESERVE_TOKENS, 1500)
    return usable * _CHARS_PER_TOKEN // 2  # leave room for the reply


def _chunk_text(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    limit = _max_chunk_chars()
    if len(text) <= limit:
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""
    for part in paragraphs:
        piece = part.strip()
        if not piece:
            continue
        if current and len(current) + len(piece) + 2 > limit:
            chunks.append(current.strip())
            current = piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current.strip():
        chunks.append(current.strip())

    # If a single paragraph is still huge, split on sentence boundaries.
    flattened: list[str] = []
    for chunk in chunks:
        if len(chunk) <= limit:
            flattened.append(chunk)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        buf = ""
        for sentence in sentences:
            if buf and len(buf) + len(sentence) + 1 > limit:
                flattened.append(buf.strip())
                buf = sentence
            else:
                buf = f"{buf} {sentence}".strip()
        if buf.strip():
            flattened.append(buf.strip())
    return flattened or [text[:limit]]


def _parse_notes_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("The model did not return JSON notes.")
        data = json.loads(match.group(0))

    scriptures = data.get("scriptures") or []
    takeaways = data.get("takeaways") or []
    if isinstance(scriptures, str):
        scriptures = [scriptures]
    if isinstance(takeaways, str):
        takeaways = [takeaways]

    return {
        "main_theme": str(data.get("main_theme") or "").strip(),
        "scriptures": [str(item).strip() for item in scriptures if str(item).strip()],
        "takeaways": [str(item).strip() for item in takeaways if str(item).strip()],
        "summary": str(data.get("summary") or "").strip(),
    }


def generate_structured_notes(transcript: str, screen_text: str = "") -> dict[str, Any]:
    chunks = _chunk_text(transcript)
    if not chunks:
        raise ValueError("Transcript is empty.")

    screen_block = ""
    if (screen_text or "").strip():
        screen_block = (
            "\n\nOn-screen text captured from the video (OCR). Treat this as part of "
            "the sermon materials, especially for scriptures and slide points:\n"
            f"{screen_text.strip()}\n"
        )

    if len(chunks) == 1:
        raw = chat_completion(
            [
                {"role": "system", "content": NOTES_SYSTEM_PROMPT},
                {"role": "user", "content": f"Sermon transcript:\n\n{chunks[0]}{screen_block}"},
            ],
            json_mode=True,
            max_tokens=1200,
            temperature=0.2,
        )
        notes = _parse_notes_json(raw)
        notes["raw_json"] = json.dumps(notes, ensure_ascii=False)
        return notes

    partials: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        raw = chat_completion(
            [
                {"role": "system", "content": NOTES_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"This is chunk {index} of {len(chunks)} from one sermon.\n\n"
                        f"{chunk}{screen_block if index == 1 else ''}"
                    ),
                },
            ],
            json_mode=True,
            max_tokens=900,
            temperature=0.2,
        )
        parsed = _parse_notes_json(raw)
        parsed.pop("raw_json", None)
        partials.append(parsed)

    merged_raw = chat_completion(
        [
            {"role": "system", "content": MERGE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(partials, ensure_ascii=False, indent=2)},
        ],
        json_mode=True,
        max_tokens=1200,
        temperature=0.2,
    )
    notes = _parse_notes_json(merged_raw)
    notes["raw_json"] = json.dumps(notes, ensure_ascii=False)
    return notes
