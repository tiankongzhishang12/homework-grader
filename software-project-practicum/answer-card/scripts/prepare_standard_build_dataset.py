from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

from extract_scanned_scores import build_openai_client, normalize_score_payload, process_one_image
from common import (
    ensure_phase1_dirs,
    iter_image_files,
    load_grader_config,
    load_template_config,
    paper_id_from_path,
    phase1_workspace_path,
    save_json,
    scanned_input_path,
)

logger = logging.getLogger(__name__)

QUESTION_IDS = ["26", "27", "28", "29", "30", "31", "32", "33"]
OBJECTIVE_KEYS = ["single_choice", "true_false", "fill_blank"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the 100-paper standard-building dataset for scoring rubric iteration.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--grader-config", type=Path, default=None, help="Optional practicum grader-config.yaml path.")
    parser.add_argument("--split-file", type=Path, default=None, help="Path to tuning_ids.txt.")
    parser.add_argument("--input-dir", type=Path, default=None, help="Override the scanned answer-card input directory.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for stage1 summaries.")
    parser.add_argument("--force-reparse", action="store_true", help="Re-run extraction even if parsed json already exists.")
    return parser.parse_args()


def default_split_file() -> Path:
    return (Path(__file__).resolve().parents[1] / "workspace" / "dataset-splits" / "tuning_ids.txt").resolve()


def default_output_dir() -> Path:
    return (Path(__file__).resolve().parents[1] / "workspace" / "standard-build").resolve()


def read_id_list(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip().lstrip("\ufeff") for line in f if line.strip()]


def build_scan_index(root: Path) -> dict[str, Path]:
    return {paper_id_from_path(path): path for path in iter_image_files(root)}


def load_existing_parsed(parsed_dir: Path, paper_id: str) -> dict[str, Any] | None:
    path = parsed_dir / f"{paper_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def total_band(total_score: float | int | None) -> str:
    if total_score is None:
        return "unknown"
    score = float(total_score)
    if score >= 85:
        return "high"
    if score >= 70:
        return "mid"
    if score >= 60:
        return "low"
    return "very_low"


def question_band(score: float | int | None, max_score: int) -> str:
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


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    checks = record.get("checks", {}) or {}
    question_scores = record.get("question_scores", {}) or {}
    section_scores = record.get("section_scores", {}) or {}
    issues = list(checks.get("issues", []) or [])
    missing_questions = [qid for qid in QUESTION_IDS if question_scores.get(qid) is None]
    objective_summary = {}
    for key in OBJECTIVE_KEYS:
        value = section_scores.get(key)
        objective_summary[key] = value
    return {
        "paper_id": record.get("paper_id"),
        "student_number": record.get("student_number"),
        "student_name": record.get("student_name"),
        "source_image": record.get("source_image"),
        "total_score": record.get("total_score"),
        "total_band": total_band(record.get("total_score")),
        "needs_review": bool(record.get("needs_review")),
        "issues": issues,
        "missing_question_scores": missing_questions,
        "question_scores": question_scores,
        "question_bands": {
            "26": question_band(question_scores.get("26"), 5),
            "27": question_band(question_scores.get("27"), 5),
            "28": question_band(question_scores.get("28"), 5),
            "29": question_band(question_scores.get("29"), 5),
            "30": question_band(question_scores.get("30"), 10),
            "31": question_band(question_scores.get("31"), 10),
            "32": question_band(question_scores.get("32"), 10),
            "33": question_band(question_scores.get("33"), 10),
        },
        "section_scores": objective_summary,
        "computed_total": checks.get("computed_total"),
        "sum_matches_total": checks.get("sum_matches_total"),
        "confidence_overall": (record.get("confidence", {}) or {}).get("overall"),
    }


def write_truth_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "paper_id",
        "student_number",
        "student_name",
        "total_score",
        "computed_total",
        "sum_matches_total",
        "needs_review",
        "confidence_overall",
        "single_choice",
        "true_false",
        "fill_blank",
        "q26",
        "q27",
        "q28",
        "q29",
        "q30",
        "q31",
        "q32",
        "q33",
        "source_image",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "paper_id": row["paper_id"],
                    "student_number": row["student_number"],
                    "student_name": row["student_name"],
                    "total_score": row["total_score"],
                    "computed_total": row["computed_total"],
                    "sum_matches_total": row["sum_matches_total"],
                    "needs_review": row["needs_review"],
                    "confidence_overall": row["confidence_overall"],
                    "single_choice": row["section_scores"]["single_choice"],
                    "true_false": row["section_scores"]["true_false"],
                    "fill_blank": row["section_scores"]["fill_blank"],
                    "q26": row["question_scores"].get("26"),
                    "q27": row["question_scores"].get("27"),
                    "q28": row["question_scores"].get("28"),
                    "q29": row["question_scores"].get("29"),
                    "q30": row["question_scores"].get("30"),
                    "q31": row["question_scores"].get("31"),
                    "q32": row["question_scores"].get("32"),
                    "q33": row["question_scores"].get("33"),
                    "source_image": row["source_image"],
                }
            )


def write_profile_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "paper_id",
        "total_band",
        "needs_review",
        "issues",
        "missing_question_scores",
        "q26_band",
        "q27_band",
        "q28_band",
        "q29_band",
        "q30_band",
        "q31_band",
        "q32_band",
        "q33_band",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "paper_id": row["paper_id"],
                    "total_band": row["total_band"],
                    "needs_review": row["needs_review"],
                    "issues": "|".join(row["issues"]),
                    "missing_question_scores": "|".join(row["missing_question_scores"]),
                    "q26_band": row["question_bands"]["26"],
                    "q27_band": row["question_bands"]["27"],
                    "q28_band": row["question_bands"]["28"],
                    "q29_band": row["question_bands"]["29"],
                    "q30_band": row["question_bands"]["30"],
                    "q31_band": row["question_bands"]["31"],
                    "q32_band": row["question_bands"]["32"],
                    "q33_band": row["question_bands"]["33"],
                }
            )


def aggregate_summary(rows: list[dict[str, Any]], missing_ids: list[str]) -> dict[str, Any]:
    total_band_counts: dict[str, int] = {}
    question_band_counts: dict[str, dict[str, int]] = {qid: {} for qid in QUESTION_IDS}
    for row in rows:
        total_band_counts[row["total_band"]] = total_band_counts.get(row["total_band"], 0) + 1
        for qid, band in row["question_bands"].items():
            question_band_counts[qid][band] = question_band_counts[qid].get(band, 0) + 1
    anomalies = [row for row in rows if row["needs_review"] or row["missing_question_scores"]]
    return {
        "paper_count": len(rows),
        "missing_scan_count": len(missing_ids),
        "missing_scan_ids": missing_ids,
        "needs_review_count": sum(1 for row in rows if row["needs_review"]),
        "sum_mismatch_count": sum(1 for row in rows if row["sum_matches_total"] is False),
        "missing_question_score_count": sum(1 for row in rows if row["missing_question_scores"]),
        "total_band_counts": total_band_counts,
        "question_band_counts": question_band_counts,
        "anomaly_ids": [row["paper_id"] for row in anomalies],
    }


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    template_config = load_template_config(args.template_config)
    grader_config = load_grader_config(args.grader_config)
    split_file = args.split_file.resolve() if args.split_file else default_split_file()
    input_dir = args.input_dir.resolve() if args.input_dir else scanned_input_path(template_config)
    workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    output_dir = args.output_dir.resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    phase1_dirs = ensure_phase1_dirs(workspace)

    target_ids = read_id_list(split_file)
    scan_index = build_scan_index(input_dir)
    client, model = build_openai_client(grader_config)

    rows: list[dict[str, Any]] = []
    missing_ids: list[str] = []
    for paper_id in target_ids:
        image_path = scan_index.get(paper_id)
        if image_path is None:
            logger.warning("Missing scan for %s", paper_id)
            missing_ids.append(paper_id)
            continue
        parsed = None if args.force_reparse else load_existing_parsed(phase1_dirs["parsed"], paper_id)
        if parsed is None:
            logger.info("Parsing %s", paper_id)
            parsed = process_one_image(image_path, template_config, client, model, phase1_dirs)
        else:
            logger.info("Reusing parsed result for %s", paper_id)
        rows.append(summarize_record(parsed))

    rows.sort(key=lambda item: item["paper_id"])
    summary = aggregate_summary(rows, missing_ids)
    anomalies = [row for row in rows if row["needs_review"] or row["missing_question_scores"]]

    save_json(
        output_dir / "tuning_truth_manifest.json",
        {
            "split_file": str(split_file),
            "summary": summary,
            "papers": rows,
        },
    )
    save_json(output_dir / "tuning_anomalies.json", {"count": len(anomalies), "items": anomalies})
    write_truth_table(output_dir / "tuning_truth_table.csv", rows)
    write_profile_table(output_dir / "tuning_sample_profile.csv", rows)
    logger.info("Prepared tuning dataset: %s papers, %s anomalies", len(rows), len(anomalies))
    logger.info("Wrote manifest to %s", output_dir / "tuning_truth_manifest.json")


if __name__ == "__main__":
    main()
