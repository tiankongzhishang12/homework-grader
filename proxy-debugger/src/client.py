from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class RequestConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 120.0
    temperature: float = 1.0
    max_output_tokens: int = 256


@dataclass
class RawCallResult:
    endpoint: str
    url: str
    request_headers: dict[str, str]
    request_body: dict[str, Any]
    status_code: int | None
    response_headers: dict[str, str]
    response_body: Any
    elapsed_ms: int
    transport_error: str = ""


def _join_url(base_url: str, suffix: str) -> str:
    return f"{base_url.rstrip('/')}/{suffix.lstrip('/')}"


def _base_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def build_responses_payload(model: str, prompt: str, temperature: float, max_output_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            }
        ],
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "text": {"format": {"type": "text"}},
    }


def build_chat_payload(model: str, prompt: str, temperature: float, max_output_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }


def post_responses(config: RequestConfig, prompt: str) -> RawCallResult:
    url = _join_url(config.base_url, "responses")
    payload = build_responses_payload(config.model, prompt, config.temperature, config.max_output_tokens)
    return _post_json("responses", url, config.api_key, config.timeout_seconds, payload)


def post_chat_completions(config: RequestConfig, prompt: str) -> RawCallResult:
    url = _join_url(config.base_url, "chat/completions")
    payload = build_chat_payload(config.model, prompt, config.temperature, config.max_output_tokens)
    return _post_json("chat", url, config.api_key, config.timeout_seconds, payload)


def _post_json(
    endpoint: str,
    url: str,
    api_key: str,
    timeout_seconds: float,
    payload: dict[str, Any],
) -> RawCallResult:
    headers = _base_headers(api_key)
    started = time.perf_counter()

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        try:
            response_body: Any = response.json()
        except Exception:
            response_body = response.text

        return RawCallResult(
            endpoint=endpoint,
            url=url,
            request_headers=headers,
            request_body=payload,
            status_code=response.status_code,
            response_headers=dict(response.headers),
            response_body=response_body,
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return RawCallResult(
            endpoint=endpoint,
            url=url,
            request_headers=headers,
            request_body=payload,
            status_code=None,
            response_headers={},
            response_body={},
            elapsed_ms=elapsed_ms,
            transport_error=str(exc),
        )
