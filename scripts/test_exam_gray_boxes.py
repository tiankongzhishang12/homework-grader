#!/usr/bin/env python3
"""Run vision-based gray-box recognition on exam question crops.

Usage:
    python test_exam_gray_boxes.py \
        --pdf workspace/cqupt-final/raw/text3.pdf \
        --config grader-config.yaml \
        --output workspace/cqupt-final/logs/gray-box-test

The script reuses the crop preset from debug_exam_crops.py, saves the crop
images, sends each crop to the configured model multiple times, and writes a
JSON report for manual comparison.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from openai import OpenAI
import yaml

from debug_exam_crops import PRESETS, export_crop, export_full_page


PROMPTS: dict[str, str] = {
    "q1": (
        'This image contains exactly one Chinese objective question, question 1. '
        'Read the selected option from the visible gray-filled answer box. '
        'Return strict JSON: {"answer":"A|B|C|D|unknown","confidence":0-1,"notes":"short"}.'
    ),
    "q2": (
        'This image contains exactly one Chinese objective question, question 2. '
        'Read all selected options from the visible gray-filled answer boxes. '
        'Return strict JSON: {"answer":["A","B"] or ["unknown"],"confidence":0-1,"notes":"short"}.'
    ),
    "q3": (
        'This image contains exactly one Chinese objective question, question 3. '
        'Read the selected option from the visible gray-filled answer box. '
        'Return strict JSON: {"answer":"A|B|C|D|unknown","confidence":0-1,"notes":"short"}.'
    ),
    "q4": (
        'This image contains exactly one Chinese objective question, question 4. '
        'Read all selected options from the visible gray-filled answer boxes. '
        'Return strict JSON: {"answer":["A","B"] or ["unknown"],"confidence":0-1,"notes":"short"}.'
    ),
    "q5": (
        'This image contains exactly one Chinese judgment question, question 5. '
        'Do not infer correctness. Only read which mark position is visibly selected. '
        'Return strict JSON: {"answer":"left|right|both|none|unknown","confidence":0-1,"notes":"short"}.'
    ),
    "q6": (
        'This image contains exactly one Chinese judgment question, question 6. '
        'Do not infer correctness. Only read which mark position is visibly selected. '
        'Return strict JSON: {"answer":"left|right|both|none|unknown","confidence":0-1,"notes":"short"}.'
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test gray-box recognition on cropped exam question blocks."
    )
    parser.add_argument("--pdf", required=True, help="Path to the source PDF.")
    parser.add_argument(
        "--config",
        default="grader-config.yaml",
        help="Path to YAML config with openai.api_key/base_url/model.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Directory to write crops and gray-box-results.json.",
    )
    parser.add_argument(
        "--preset",
        default="cqupt_page1_v1",
        choices=sorted(PRESETS.keys()),
        help="Built-in crop preset to reuse.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="How many independent model calls to make per question.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="How many retries to attempt inside a single model call.",
    )
    return parser.parse_args()


def load_client_and_model(config_path: Path) -> tuple[OpenAI, str]:
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    openai_cfg = config.get("openai", {})
    client = OpenAI(
        api_key=openai_cfg.get("api_key", ""),
        base_url=openai_cfg.get("base_url") or None,
    )
    model = str(openai_cfg.get("model", "gpt-5.4"))
    return client, model


def encode_crop_image(crop_path: Path) -> str:
    return base64.b64encode(crop_path.read_bytes()).decode("ascii")


def call_model(
    client: OpenAI,
    model: str,
    prompt_text: str,
    image_b64: str,
    retries: int,
) -> dict[str, Any]:
    last_error = ""
    for attempt in range(retries):
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "You are testing whether a vision model can read gray-filled "
                                    "answer boxes on a Chinese exam paper. Return strict JSON only."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt_text},
                            {
                                "type": "input_image",
                                "image_url": "data:image/png;base64," + image_b64,
                            },
                        ],
                    },
                ],
                max_output_tokens=200,
            )
            return {
                "ok": True,
                "text": response.output_text.strip(),
            }
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(2 + attempt * 2)

    return {
        "ok": False,
        "error": last_error,
    }


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf)
    config_path = Path(args.config)
    output_dir = Path(args.output)
    preset = PRESETS[args.preset]

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    client, model = load_client_and_model(config_path)

    doc = fitz.open(pdf_path)
    page_index = int(preset["page_index"])
    page = doc.load_page(page_index)

    full_page_path = output_dir / f"page{page_index + 1}-full.png"
    export_full_page(page, full_page_path, float(preset["full_page_zoom"]))

    results: dict[str, Any] = {
        "pdf": str(pdf_path),
        "config": str(config_path),
        "model": model,
        "preset": args.preset,
        "page_index": page_index,
        "full_page_image": str(full_page_path),
        "questions": {},
    }

    for qid, rel_box in preset["questions"].items():
        crop_path = output_dir / f"{qid}.png"
        export_crop(page, rel_box, crop_path, float(preset["crop_zoom"]))
        image_b64 = encode_crop_image(crop_path)

        runs: list[dict[str, Any]] = []
        prompt_text = PROMPTS.get(qid)
        if not prompt_text:
            runs.append({"ok": False, "error": f"No prompt configured for {qid}"})
        else:
            for _ in range(args.runs):
                runs.append(call_model(client, model, prompt_text, image_b64, args.retries))

        results["questions"][qid] = {
            "crop_file": str(crop_path),
            "runs": runs,
        }

    result_path = output_dir / "gray-box-results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
