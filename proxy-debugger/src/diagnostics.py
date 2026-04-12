from __future__ import annotations

from typing import Any


def diagnose(response_body: Any, parsed_text: str, transport_error: str = "") -> list[str]:
    issues: list[str] = []

    if transport_error:
        issues.append("transport_error")
        return issues

    if not isinstance(response_body, dict):
        issues.append("non_json_response")
        return issues

    if not parsed_text:
        issues.append("no_text_extracted")

    status = response_body.get("status")
    output = response_body.get("output")
    usage = response_body.get("usage", {})

    if status == "completed" and isinstance(output, list) and len(output) == 0:
        issues.append("completed_but_empty_output")

    output_tokens = 0
    if isinstance(usage, dict):
        try:
            output_tokens = int(usage.get("output_tokens", 0) or 0)
        except Exception:
            output_tokens = 0

    if output_tokens > 0 and not parsed_text:
        issues.append("tokens_present_but_no_text")

    choices = response_body.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message", {})
            if isinstance(message, dict) and message.get("content") is None:
                issues.append("chat_content_null")

    known_shape = any(key in response_body for key in ("output", "output_text", "choices"))
    if not known_shape:
        issues.append("non_standard_response_shape")

    return sorted(set(issues))
