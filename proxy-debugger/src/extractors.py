from __future__ import annotations

from typing import Any


def extract_text(response_body: Any) -> str:
    if not isinstance(response_body, dict):
        return ""

    responses_text = _extract_from_responses(response_body)
    if responses_text:
        return responses_text

    chat_text = _extract_from_chat_completions(response_body)
    if chat_text:
        return chat_text

    return ""


def _extract_from_responses(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text_value = content.get("text")
            if isinstance(text_value, str) and text_value.strip():
                chunks.append(text_value.strip())
    return "\n".join(chunks).strip()


def _extract_from_chat_completions(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", []) or []
    if not isinstance(choices, list):
        return ""

    chunks: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            chunks.append(content.strip())
    return "\n".join(chunks).strip()
