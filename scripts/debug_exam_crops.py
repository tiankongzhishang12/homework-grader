#!/usr/bin/env python3
"""Export full exam pages and question crops for manual crop debugging.

Usage:
    python debug_exam_crops.py --pdf workspace/cqupt-final/raw/text3.pdf --output workspace/cqupt-final/logs/crop-debug

The default preset targets page 1 of the current CQUPT final-exam layout.
It exports:
  - one full-page PNG per referenced page
  - one crop PNG per configured question block
  - crops.json (relative and absolute crop rectangles)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


DEFAULT_PRESET = "cqupt_page1_v1"


PRESETS: dict[str, dict[str, Any]] = {
    "cqupt_page1_v1": {
        "page_index": 0,
        "full_page_zoom": 3.5,
        "crop_zoom": 3.5,
        "description": (
            "CQUPT final-exam page-1 object-question blocks. Each crop keeps one "
            "question stem and the answer boxes directly below it."
        ),
        "questions": {
            "q1": (0.04, 0.18, 0.51, 0.49),
            "q2": (0.04, 0.47, 0.51, 0.70),
            "q3": (0.04, 0.69, 0.51, 0.95),
            "q4": (0.51, 0.03, 0.96, 0.31),
            "q5": (0.51, 0.31, 0.96, 0.43),
            "q6": (0.51, 0.43, 0.96, 0.51),
        },
    }
    ,
    "cqupt_subjective_v1": {
        "full_page_zoom": 3.0,
        "crop_zoom": 3.5,
        "description": (
            "CQUPT final-exam subjective-answer blocks. This preset follows the "
            "current manual layout assumptions: q8 is below q7 on page 1; page 2 "
            "uses a left-right layout where q9 sits above the comprehensive "
            "section, programming is in the left upper-middle area, algorithm is "
            "split across the left lower area and the right upper area, and "
            "white-box testing is in the right lower area."
        ),
        "blocks": {
            # Assumptions from the current manual inspection workflow.
            # These are intentionally broad crops for visual verification first.
            "q8": [
                {"page_index": 0, "rect": (0.52, 0.58, 0.98, 0.96)},
            ],
            "q9": [
                {"page_index": 1, "rect": (0.04, 0.04, 0.47, 0.20)},
            ],
            "programming_01": [
                {"page_index": 1, "rect": (0.02, 0.22, 0.52, 0.72)},
            ],
            "algorithm_01": [
                {"page_index": 1, "rect": (0.02, 0.74, 0.52, 0.96)},
                {"page_index": 1, "rect": (0.52, 0.05, 0.97, 0.46)},
            ],
            "white_box_testing_01": [
                {"page_index": 1, "rect": (0.46, 0.44, 0.97, 0.95)},
            ],
        },
    },
    "cqupt_subjective_text1_v1": {
        "full_page_zoom": 3.0,
        "crop_zoom": 3.5,
        "description": (
            "CQUPT final-exam subjective-answer blocks for text1.pdf. Page 1 keeps "
            "q8 below q7. On page 2, q9 stays above the comprehensive section, "
            "programming is in the left lower area, algorithm sits above the "
            "white-box section on the right, and white-box testing occupies the "
            "right lower area."
        ),
        "blocks": {
            "q8": [
                {"page_index": 0, "rect": (0.52, 0.58, 0.98, 0.96)},
            ],
            "q9": [
                {"page_index": 1, "rect": (0.04, 0.10, 0.52, 0.30)},
            ],
            "programming_01": [
                {"page_index": 1, "rect": (0.02, 0.32, 0.52, 0.96)},
            ],
            "algorithm_01": [
                {"page_index": 1, "rect": (0.50, 0.10, 0.90, 0.50)},
            ],
            "white_box_testing_01": [
                {"page_index": 1, "rect": (0.46, 0.54, 0.97, 0.95)},
            ],
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export full-page and per-question crops for manual verification."
    )
    parser.add_argument("--pdf", required=True, help="Path to the source PDF.")
    parser.add_argument(
        "--output",
        required=True,
        help="Directory to write the debug images and crops.json.",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        choices=sorted(PRESETS.keys()),
        help="Built-in crop preset to use.",
    )
    return parser.parse_args()


def rel_to_abs(page_rect: fitz.Rect, rel_box: tuple[float, float, float, float]) -> fitz.Rect:
    x0, y0, x1, y1 = rel_box
    return fitz.Rect(
        page_rect.x0 + page_rect.width * x0,
        page_rect.y0 + page_rect.height * y0,
        page_rect.x0 + page_rect.width * x1,
        page_rect.y0 + page_rect.height * y1,
    )


def export_full_page(page: fitz.Page, out_path: Path, zoom: float) -> None:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(out_path)


def export_crop(page: fitz.Page, rel_box: tuple[float, float, float, float], out_path: Path, zoom: float) -> fitz.Rect:
    abs_rect = rel_to_abs(page.rect, rel_box)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=abs_rect, alpha=False)
    pix.save(out_path)
    return abs_rect


def _iter_preset_pages(preset: dict[str, Any]) -> list[int]:
    if "page_index" in preset:
        return [int(preset["page_index"])]

    pages: set[int] = set()
    for parts in preset.get("blocks", {}).values():
        for part in parts:
            pages.add(int(part["page_index"]))
    return sorted(pages)


def _normalize_blocks(preset: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if "questions" in preset:
        page_index = int(preset["page_index"])
        return {
            qid: [{"page_index": page_index, "rect": rel_box}]
            for qid, rel_box in preset["questions"].items()
        }

    normalized: dict[str, list[dict[str, Any]]] = {}
    for qid, parts in preset.get("blocks", {}).items():
        normalized[qid] = [
            {
                "page_index": int(part["page_index"]),
                "rect": tuple(part["rect"]),
            }
            for part in parts
        ]
    return normalized


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf)
    output_dir = Path(args.output)
    preset = PRESETS[args.preset]

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    referenced_pages = _iter_preset_pages(preset)
    if not referenced_pages:
        raise ValueError(f"Preset {args.preset} does not define any pages or blocks.")
    for page_index in referenced_pages:
        if page_index < 0 or page_index >= doc.page_count:
            raise ValueError(
                f"Preset references page_index={page_index}, but {pdf_path} has "
                f"page_count={doc.page_count}"
            )

    manifest: dict[str, Any] = {
        "pdf": str(pdf_path),
        "preset": args.preset,
        "description": preset["description"],
        "page_indices": referenced_pages,
        "full_page_images": {},
        "page_rects": {},
        "crops": {},
    }

    pages: dict[int, fitz.Page] = {}
    for page_index in referenced_pages:
        page = doc.load_page(page_index)
        pages[page_index] = page
        full_page_path = output_dir / f"page{page_index + 1}-full.png"
        export_full_page(page, full_page_path, float(preset["full_page_zoom"]))
        manifest["full_page_images"][str(page_index)] = str(full_page_path)
        manifest["page_rects"][str(page_index)] = {
            "x0": page.rect.x0,
            "y0": page.rect.y0,
            "x1": page.rect.x1,
            "y1": page.rect.y1,
            "width": page.rect.width,
            "height": page.rect.height,
        }

    normalized_blocks = _normalize_blocks(preset)
    for qid, parts in normalized_blocks.items():
        crop_entries: list[dict[str, Any]] = []
        for idx, part in enumerate(parts, start=1):
            page_index = int(part["page_index"])
            rel_box = tuple(part["rect"])
            page = pages[page_index]

            suffix = f"-p{page_index + 1}"
            if len(parts) > 1:
                suffix += f"-part{idx}"
            crop_path = output_dir / f"{qid}{suffix}.png"
            abs_rect = export_crop(page, rel_box, crop_path, float(preset["crop_zoom"]))
            crop_entries.append(
                {
                    "file": str(crop_path),
                    "page_index": page_index,
                    "part_index": idx,
                    "relative_rect": {
                        "x0": rel_box[0],
                        "y0": rel_box[1],
                        "x1": rel_box[2],
                        "y1": rel_box[3],
                    },
                    "absolute_rect": {
                        "x0": abs_rect.x0,
                        "y0": abs_rect.y0,
                        "x1": abs_rect.x1,
                        "y1": abs_rect.y1,
                        "width": abs_rect.width,
                        "height": abs_rect.height,
                    },
                }
            )

        manifest["crops"][qid] = crop_entries if len(crop_entries) > 1 else crop_entries[0]

    manifest_path = output_dir / "crops.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
