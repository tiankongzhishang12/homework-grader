from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from PIL import Image

from common import (
    ANSWER_CARD_ROOT,
    load_template_config,
    paper_id_from_path,
    phase1_workspace_path,
    read_image,
    save_json,
)
from extract_scanned_scores import create_red_mask, normalize_scan

logger = logging.getLogger(__name__)

QUESTION_MAX_SCORE = {
    "26": 5,
    "27": 5,
    "28": 5,
    "29": 5,
    "30": 10,
    "31": 10,
    "32": 10,
    "33": 10,
}

SUBJECTIVE_ANSWER_REGIONS = {
    # Coordinates are in normalized 2199x3110 scan space.
    "26": {"x": 25, "y": 1000, "w": 1010, "h": 490},
    "27": {"x": 1170, "y": 55, "w": 1000, "h": 360},
    "28": {"x": 1170, "y": 455, "w": 1000, "h": 520},
    "29": {"x": 1170, "y": 785, "w": 1000, "h": 510},
    "30": {"x": 25, "y": 1300, "w": 1010, "h": 630},
    "31": {"x": 25, "y": 1970, "w": 1010, "h": 865},
    "32": {"x": 1170, "y": 1300, "w": 1000, "h": 610},
    "33": {"x": 1170, "y": 1970, "w": 1000, "h": 890},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract subjective answer samples grouped by teacher score.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override answer inference output directory.")
    parser.add_argument("--split-file", type=Path, default=None, help="Optional paper id list used to filter parsed records.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N parsed phase1 records.")
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="Include phase1 records marked needs_review when subjective question scores are still present.",
    )
    return parser.parse_args()


def answer_inference_workspace(override: Path | None) -> Path:
    if override:
        return override.resolve()
    return (ANSWER_CARD_ROOT / "workspace" / "answer-inference").resolve()


def ensure_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "root": output_dir,
        "subjective_crops": output_dir / "subjective-crops",
        "subjective_reports": output_dir / "subjective-reports",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def read_id_list(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        return {line.strip().lstrip("\ufeff") for line in f if line.strip()}


def load_phase1_results(
    parsed_dir: Path,
    limit: int | None = None,
    include_review: bool = False,
    allowed_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(parsed_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        paper_id = str(payload.get("paper_id", "")).strip()
        if allowed_ids is not None and paper_id not in allowed_ids:
            continue
        if payload.get("needs_review") and not include_review:
            continue
        if not payload.get("question_scores"):
            continue
        results.append(payload)
        if limit and len(results) >= limit:
            break
    return results


def score_bucket(score: float | int | None, max_score: int) -> str:
    if score is None:
        return "unknown"
    value = float(score)
    if value == 0:
        return "zero"
    if value == max_score:
        return "full"
    ratio = value / max_score
    if ratio >= 0.8:
        return "high"
    if ratio >= 0.5:
        return "mid"
    return "low"


def crop_question_images(normalized: Image.Image, qid: str) -> dict[str, Image.Image]:
    region = SUBJECTIVE_ANSWER_REGIONS[qid]
    box = (
        int(region["x"]),
        int(region["y"]),
        int(region["x"] + region["w"]),
        int(region["y"] + region["h"]),
    )
    red_mask = create_red_mask(normalized)
    return {
        "original": normalized.crop(box),
        "red_mask": red_mask.crop(box),
    }


def save_question_crops(output_dir: Path, paper_id: str, qid: str, images: dict[str, Image.Image]) -> dict[str, str]:
    paper_dir = output_dir / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for variant, image in images.items():
        path = paper_dir / f"q{qid}-{variant}.png"
        image.save(path)
        paths[variant] = str(path)
    return paths


def process_result(result: dict[str, Any], template_config: dict[str, Any], dirs: dict[str, Path]) -> list[dict[str, Any]]:
    source_image = Path(str(result.get("source_image", "")))
    if not source_image.exists():
        logger.warning("Missing source image: %s", source_image)
        return []
    paper_id = str(result.get("paper_id") or paper_id_from_path(source_image))
    image = read_image(source_image)
    normalized, normalize_debug = normalize_scan(image, template_config.get("template", {}) or {})
    question_scores = result.get("question_scores", {}) or {}
    samples: list[dict[str, Any]] = []
    for qid, max_score in QUESTION_MAX_SCORE.items():
        score = question_scores.get(qid)
        images = crop_question_images(normalized, qid)
        crop_paths = save_question_crops(dirs["subjective_crops"], paper_id, qid, images)
        samples.append(
            {
                "paper_id": paper_id,
                "student_number": result.get("student_number", ""),
                "student_name": result.get("student_name", ""),
                "source_image": str(source_image),
                "question_id": qid,
                "score": score,
                "max_score": max_score,
                "bucket": score_bucket(score, max_score),
                "crop_paths": crop_paths,
                "normalization": normalize_debug,
            }
        )
    return samples


def aggregate_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, Any] = {
        qid: {
            "max_score": max_score,
            "buckets": {"full": [], "high": [], "mid": [], "low": [], "zero": [], "unknown": []},
            "score_distribution": {},
        }
        for qid, max_score in QUESTION_MAX_SCORE.items()
    }
    for sample in samples:
        qid = str(sample["question_id"])
        bucket = str(sample["bucket"])
        grouped[qid]["buckets"].setdefault(bucket, []).append(sample)
        score_key = str(sample.get("score"))
        grouped[qid]["score_distribution"][score_key] = grouped[qid]["score_distribution"].get(score_key, 0) + 1
    return {
        "metadata": {
            "sample_count": len(samples),
            "paper_count": len({sample["paper_id"] for sample in samples}),
        },
        "questions": grouped,
    }


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    template_config = load_template_config(args.template_config)
    phase1_workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    output_dir = answer_inference_workspace(args.output_dir)
    dirs = ensure_dirs(output_dir)
    allowed_ids = read_id_list(args.split_file.resolve()) if args.split_file else None
    phase1_results = load_phase1_results(phase1_workspace / "parsed", args.limit, args.include_review, allowed_ids)
    all_samples: list[dict[str, Any]] = []
    for result in phase1_results:
        all_samples.extend(process_result(result, template_config, dirs))
        logger.info("Extracted subjective samples for %s", result.get("paper_id", "unknown"))
    aggregate = aggregate_samples(all_samples)
    save_json(output_dir / "subjective_samples.json", aggregate)
    logger.info("Wrote subjective samples to %s", output_dir / "subjective_samples.json")


if __name__ == "__main__":
    main()
