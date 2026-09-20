"""Contextual Q&A over a sermon transcript and generated notes."""

from __future__ import annotations

from backend.core.config import LLM_N_CTX
from backend.services.llm import chat_completion

CHAT_SYSTEM_PROMPT = """You are a study partner helping a church member understand a sermon.
Answer from the provided transcript and generated notes. If the answer is not in that
material, say you do not find it in this sermon instead of guessing.

Be concise, pastoral in tone, and quote short phrases from the transcript when helpful.
Do not invent scripture references.
"""

_CHARS_PER_TOKEN = 4


def _trim_to_budget(text: str, max_chars: int) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... transcript truncated ...]\n\n" + text[-half:]


def answer_question(
    *,
    transcript: str,
    notes_json: str,
    user_notes: str,
    history: list[dict[str, str]],
    question: str,
) -> str:
    history_budget = 4000
    packed_history = []
    used = 0
    for message in reversed(history):
        size = len(message.get("content") or "")
        if used + size > history_budget:
            break
        packed_history.append(message)
        used += size
    packed_history.reverse()

    remaining_tokens = max(LLM_N_CTX - 1500 - used // _CHARS_PER_TOKEN, 800)
    transcript_chars = remaining_tokens * _CHARS_PER_TOKEN // 2

    context = (
        f"Generated notes JSON:\n{notes_json}\n\n"
        f"User's personal notes:\n{user_notes or '(none)'}\n\n"
        f"Sermon transcript:\n{_trim_to_budget(transcript, transcript_chars)}"
    )
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": context},
        {"role": "assistant", "content": "I have the sermon notes and transcript. Ask your question."},
        *packed_history,
        {"role": "user", "content": question},
    ]
    return chat_completion(messages, json_mode=False, max_tokens=700, temperature=0.4)
