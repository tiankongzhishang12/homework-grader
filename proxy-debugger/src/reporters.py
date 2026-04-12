from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .client import RawCallResult


def build_record(result: RawCallResult, parsed_text: str, diagnostics: list[str]) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().astimezone().isoformat(),
        "endpoint": result.endpoint,
        "url": result.url,
        "status_code": result.status_code,
        "elapsed_ms": result.elapsed_ms,
        "transport_error": result.transport_error,
        "parsed_text": parsed_text,
        "diagnostics": diagnostics,
        "request": {
            "headers": result.request_headers,
            "body": result.request_body,
        },
        "response": {
            "headers": result.response_headers,
            "body": result.response_body,
        },
    }


def save_record(output_dir: Path, record: dict[str, Any], label: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in label).strip("-") or "result"
    path = output_dir / f"{stamp}-{safe_label}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_summary(record: dict[str, Any], saved_path: Path | None = None) -> None:
    endpoint = record.get("endpoint", "unknown")
    status_code = record.get("status_code")
    elapsed_ms = record.get("elapsed_ms")
    parsed_text = str(record.get("parsed_text", "") or "")
    diagnostics = record.get("diagnostics", []) or []
    transport_error = record.get("transport_error", "")

    print(f"Endpoint: {endpoint}")
    print(f"Status: {status_code if status_code is not None else 'transport-error'}")
    print(f"Elapsed: {elapsed_ms} ms")
    print(f"Text extracted: {'yes' if parsed_text else 'no'}")
    print(f"Diagnostics: {', '.join(diagnostics) if diagnostics else 'none'}")
    if transport_error:
        print(f"Transport error: {transport_error}")
    if parsed_text:
        print("Parsed text:")
        print(parsed_text)
    if saved_path is not None:
        print(f"Saved: {saved_path}")
