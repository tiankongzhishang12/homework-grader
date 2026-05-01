from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from common import ANSWER_CARD_ROOT, ensure_phase1_dirs, load_template_config, phase1_workspace_path

logger = logging.getLogger(__name__)

DEFAULT_SPLIT_PATH = ANSWER_CARD_ROOT / "workspace" / "dataset-splits" / "validation_ids.txt"
DEFAULT_OUTPUT_DIR = ANSWER_CARD_ROOT / "workspace" / "validation-run"

SECTION_KEYS = ["single_choice", "true_false", "fill_blank", "short_answer", "comprehensive"]
QUESTION_KEYS = [str(i) for i in range(26, 34)]

SECTION_LABELS = {
    "single_choice": "单选题得分",
    "true_false": "判断题得分",
    "fill_blank": "填空题得分",
    "short_answer": "简答题得分",
    "comprehensive": "综合题得分",
}

OVERVIEW_METRIC_LABELS = {
    "validation_paper_count": "验证集试卷数",
    "loaded_teacher_truth_count": "已加载教师真值数",
    "needs_review_count": "需要复核数量",
    "sum_mismatch_count": "总分不一致数量",
    "teacher_total_avg": "教师总分平均值",
    "teacher_total_min": "教师总分最低分",
    "teacher_total_max": "教师总分最高分",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export validation-set teacher truth and optional system scoring comparison to Excel."
    )
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument("--split-file", type=Path, default=DEFAULT_SPLIT_PATH, help="Validation split id list.")
    parser.add_argument("--system-results", type=Path, default=None, help="Optional JSON/CSV system scoring results.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory to write xlsx/csv files.")
    parser.add_argument("--also-export-csv", action="store_true", help="Also export CSV files in addition to xlsx.")
    return parser.parse_args()


def read_id_list(path: Path) -> list[str]:
    ids: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            text = line.strip().lstrip("\ufeff")
            if text:
                ids.append(text)
    return ids


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_parsed_results(parsed_dir: Path, selected_ids: list[str]) -> list[dict[str, Any]]:
    selected_set = set(selected_ids)
    by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(parsed_dir.glob("*.json")):
        item = load_json(path)
        paper_id = str(item.get("paper_id", "")).strip()
        if paper_id in selected_set:
            by_id[paper_id] = item
    missing = [paper_id for paper_id in selected_ids if paper_id not in by_id]
    if missing:
        raise FileNotFoundError(f"Missing phase1 parsed files for {len(missing)} papers: {missing[:5]}")
    return [by_id[paper_id] for paper_id in selected_ids]


def safe_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def build_teacher_summary_df(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in results:
        section_scores = item.get("section_scores", {}) or {}
        question_scores = item.get("question_scores", {}) or {}
        checks = item.get("checks", {}) or {}
        confidence = item.get("confidence", {}) or {}
        row: dict[str, Any] = {
            "paper_id": item.get("paper_id", ""),
            "student_number": item.get("student_number", ""),
            "student_name": item.get("student_name", ""),
            "teacher_total": item.get("total_score"),
            "teacher_single_choice": section_scores.get("single_choice"),
            "teacher_true_false": section_scores.get("true_false"),
            "teacher_fill_blank": section_scores.get("fill_blank"),
            "teacher_short_answer": section_scores.get("short_answer"),
            "teacher_comprehensive": section_scores.get("comprehensive"),
            "computed_total": checks.get("computed_total"),
            "sum_matches_total": checks.get("sum_matches_total"),
            "needs_review": item.get("needs_review"),
            "confidence_overall": confidence.get("overall"),
            "issues": " | ".join(checks.get("issues", []) or []),
            "notes": " | ".join(item.get("notes", []) or []),
            "source_image": item.get("source_image", ""),
        }
        for qid in QUESTION_KEYS:
            row[f"teacher_q{qid}"] = question_scores.get(qid)
        rows.append(row)
    return pd.DataFrame(rows)


def build_teacher_question_df(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in results:
        question_scores = item.get("question_scores", {}) or {}
        for qid in QUESTION_KEYS:
            rows.append(
                {
                    "paper_id": item.get("paper_id", ""),
                    "student_number": item.get("student_number", ""),
                    "student_name": item.get("student_name", ""),
                    "question_id": qid,
                    "teacher_score": question_scores.get(qid),
                    "max_score": 5 if qid in {"26", "27", "28", "29"} else 10,
                }
            )
    return pd.DataFrame(rows)


def build_overview_df(results: list[dict[str, Any]], selected_ids: list[str]) -> pd.DataFrame:
    teacher_totals = [safe_number(item.get("total_score")) for item in results]
    teacher_totals = [value for value in teacher_totals if value is not None]
    needs_review_count = sum(bool(item.get("needs_review")) for item in results)
    sum_mismatch_count = sum(not bool((item.get("checks", {}) or {}).get("sum_matches_total")) for item in results)
    rows = [
        {"metric": "validation_paper_count", "value": len(selected_ids)},
        {"metric": "loaded_teacher_truth_count", "value": len(results)},
        {"metric": "needs_review_count", "value": needs_review_count},
        {"metric": "sum_mismatch_count", "value": sum_mismatch_count},
        {"metric": "teacher_total_avg", "value": round(sum(teacher_totals) / len(teacher_totals), 2) if teacher_totals else None},
        {"metric": "teacher_total_min", "value": min(teacher_totals) if teacher_totals else None},
        {"metric": "teacher_total_max", "value": max(teacher_totals) if teacher_totals else None},
    ]
    return pd.DataFrame(rows)


def normalize_system_result(item: dict[str, Any]) -> dict[str, Any]:
    section_scores = item.get("section_scores", {}) or {}
    question_scores = item.get("question_scores", {}) or {}
    return {
        "paper_id": str(item.get("paper_id", "")).strip(),
        "system_total": item.get("system_total", item.get("total_score")),
        "section_scores": section_scores,
        "question_scores": question_scores,
        "review_required": item.get("review_required", item.get("needs_review")),
        "review_reason": item.get("review_reason", item.get("issues", "")),
        "evidence": item.get("evidence", ""),
    }


def load_system_results(path: Path) -> dict[str, dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = load_json(path)
        if isinstance(payload, dict) and "results" in payload:
            records = payload["results"]
        elif isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = list(payload.values())
        else:
            raise ValueError(f"Unsupported system results json format: {path}")
        normalized = [normalize_system_result(item) for item in records if isinstance(item, dict)]
        return {item["paper_id"]: item for item in normalized if item["paper_id"]}

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        results: dict[str, dict[str, Any]] = {}
        for _, row in df.iterrows():
            paper_id = str(row.get("paper_id", "")).strip()
            if not paper_id:
                continue
            section_scores = {key: row.get(f"system_{key}") for key in SECTION_KEYS if f"system_{key}" in df.columns}
            question_scores = {qid: row.get(f"system_q{qid}") for qid in QUESTION_KEYS if f"system_q{qid}" in df.columns}
            results[paper_id] = {
                "paper_id": paper_id,
                "system_total": row.get("system_total"),
                "section_scores": section_scores,
                "question_scores": question_scores,
                "review_required": row.get("review_required"),
                "review_reason": row.get("review_reason", ""),
                "evidence": row.get("evidence", ""),
            }
        return results

    raise ValueError(f"Unsupported system results format: {path}")


def build_compare_summary_df(
    teacher_df: pd.DataFrame, system_results: dict[str, dict[str, Any]]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, teacher in teacher_df.iterrows():
        paper_id = teacher["paper_id"]
        system = system_results.get(str(paper_id))
        row: dict[str, Any] = teacher.to_dict()
        if system:
            row["system_total"] = safe_number(system.get("system_total"))
            teacher_total = safe_number(row.get("teacher_total"))
            system_total = safe_number(row.get("system_total"))
            row["total_diff"] = None if teacher_total is None or system_total is None else system_total - teacher_total
            row["abs_total_diff"] = None if row["total_diff"] is None else abs(row["total_diff"])
            for key in SECTION_KEYS:
                row[f"system_{key}"] = safe_number((system.get("section_scores") or {}).get(key))
            for qid in QUESTION_KEYS:
                teacher_score = safe_number(row.get(f"teacher_q{qid}"))
                system_score = safe_number((system.get("question_scores") or {}).get(qid))
                row[f"system_q{qid}"] = system_score
                row[f"diff_q{qid}"] = None if teacher_score is None or system_score is None else system_score - teacher_score
            row["review_required"] = system.get("review_required")
            row["review_reason"] = system.get("review_reason", "")
            row["evidence"] = system.get("evidence", "")
        rows.append(row)
    return pd.DataFrame(rows)


def build_question_metrics_df(compare_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for qid in QUESTION_KEYS:
        teacher_col = f"teacher_q{qid}"
        system_col = f"system_q{qid}"
        if teacher_col not in compare_df.columns or system_col not in compare_df.columns:
            continue
        pair_df = compare_df[[teacher_col, system_col]].dropna()
        if pair_df.empty:
            continue
        diffs = pair_df[system_col] - pair_df[teacher_col]
        abs_diffs = diffs.abs()
        rows.append(
            {
                "question_id": qid,
                "sample_count": len(pair_df),
                "teacher_avg": round(float(pair_df[teacher_col].mean()), 3),
                "system_avg": round(float(pair_df[system_col].mean()), 3),
                "mae": round(float(abs_diffs.mean()), 3),
                "exact_match_rate": round(float((abs_diffs == 0).mean()), 3),
                "tolerance_match_rate_0_5": round(float((abs_diffs <= 0.5).mean()), 3),
                "tolerance_match_rate_1_0": round(float((abs_diffs <= 1.0).mean()), 3),
                "bias_direction": "higher" if diffs.mean() > 0 else "lower" if diffs.mean() < 0 else "equal",
            }
        )
    return pd.DataFrame(rows)


def build_worst_cases_df(compare_df: pd.DataFrame) -> pd.DataFrame:
    if "abs_total_diff" not in compare_df.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    sortable = compare_df.dropna(subset=["abs_total_diff"]).sort_values("abs_total_diff", ascending=False)
    for _, row in sortable.head(20).iterrows():
        q_diffs: list[tuple[str, float]] = []
        for qid in QUESTION_KEYS:
            diff = safe_number(row.get(f"diff_q{qid}"))
            if diff is not None:
                q_diffs.append((qid, abs(diff)))
        q_diffs.sort(key=lambda item: item[1], reverse=True)
        largest_error_questions = ", ".join(f"Q{qid}" for qid, value in q_diffs[:3] if value > 0)
        rows.append(
            {
                "paper_id": row.get("paper_id"),
                "student_name": row.get("student_name"),
                "teacher_total": row.get("teacher_total"),
                "system_total": row.get("system_total"),
                "abs_total_diff": row.get("abs_total_diff"),
                "largest_error_questions": largest_error_questions,
                "review_required": row.get("review_required"),
                "review_reason": row.get("review_reason", ""),
            }
        )
    return pd.DataFrame(rows)


def localize_overview_df(df: pd.DataFrame) -> pd.DataFrame:
    localized = df.copy()
    if "metric" in localized.columns:
        localized["metric"] = localized["metric"].map(lambda x: OVERVIEW_METRIC_LABELS.get(str(x), str(x)))
    return localized.rename(columns={"metric": "指标", "value": "数值"})


def localize_teacher_summary_df(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "paper_id": "试卷编号",
        "student_number": "学号",
        "student_name": "姓名",
        "teacher_total": "教师总分",
        "computed_total": "分项计算总分",
        "sum_matches_total": "总分是否一致",
        "needs_review": "需要复核",
        "confidence_overall": "抽取置信度",
        "issues": "异常问题",
        "notes": "抽取说明",
        "source_image": "原图路径",
        "system_total": "系统总分",
        "total_diff": "总分差值",
        "abs_total_diff": "总分绝对误差",
        "review_required": "系统建议复核",
        "review_reason": "复核原因",
        "evidence": "评分证据",
    }
    for key, label in SECTION_LABELS.items():
        rename_map[f"teacher_{key}"] = f"教师{label}"
        rename_map[f"system_{key}"] = f"系统{label}"
    for qid in QUESTION_KEYS:
        rename_map[f"teacher_q{qid}"] = f"教师Q{qid}"
        rename_map[f"system_q{qid}"] = f"系统Q{qid}"
        rename_map[f"diff_q{qid}"] = f"Q{qid}差值"
    return df.rename(columns=rename_map)


def build_compare_export_df(df: pd.DataFrame) -> pd.DataFrame:
    localized = localize_teacher_summary_df(df)
    ordered_columns: list[str] = [
        "姓名",
        "学号",
        "试卷编号",
        "教师总分",
        "系统总分",
        "总分差值",
        "总分绝对误差",
    ]
    for qid in QUESTION_KEYS:
        ordered_columns.append(f"教师Q{qid}")
    for qid in QUESTION_KEYS:
        ordered_columns.append(f"系统Q{qid}")
    for qid in QUESTION_KEYS:
        ordered_columns.append(f"Q{qid}差值")
    ordered_columns.extend(
        [
            "系统建议复核",
            "复核原因",
            "评分证据",
        ]
    )
    existing = [column for column in ordered_columns if column in localized.columns]
    remainder = [column for column in localized.columns if column not in existing]
    return localized[existing + remainder]


def localize_teacher_question_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "paper_id": "试卷编号",
            "student_number": "学号",
            "student_name": "姓名",
            "question_id": "题号",
            "teacher_score": "教师得分",
            "max_score": "满分",
        }
    )


def localize_question_metrics_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "question_id": "题号",
            "sample_count": "样本数",
            "teacher_avg": "教师平均分",
            "system_avg": "系统平均分",
            "mae": "平均绝对误差",
            "exact_match_rate": "完全命中率",
            "tolerance_match_rate_0_5": "0.5分容差命中率",
            "tolerance_match_rate_1_0": "1.0分容差命中率",
            "bias_direction": "偏差方向",
        }
    )


def localize_worst_cases_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "paper_id": "试卷编号",
            "student_name": "姓名",
            "teacher_total": "教师总分",
            "system_total": "系统总分",
            "abs_total_diff": "总分绝对误差",
            "largest_error_questions": "误差最大题目",
            "review_required": "系统建议复核",
            "review_reason": "复核原因",
        }
    )


def export_validation_report(
    workspace: Path,
    split_file: Path,
    output_dir: Path,
    system_results_path: Path | None = None,
    also_export_csv: bool = False,
) -> Path:
    dirs = ensure_phase1_dirs(workspace)
    selected_ids = read_id_list(split_file)
    results = load_parsed_results(dirs["parsed"], selected_ids)

    teacher_summary_df = build_teacher_summary_df(results)
    teacher_question_df = build_teacher_question_df(results)
    overview_df = build_overview_df(results, selected_ids)
    overview_export_df = localize_overview_df(overview_df)
    teacher_summary_export_df = localize_teacher_summary_df(teacher_summary_df)
    teacher_question_export_df = localize_teacher_question_df(teacher_question_df)

    output_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = output_dir / "validation_report.xlsx"

    compare_summary_df = pd.DataFrame()
    question_metrics_df = pd.DataFrame()
    worst_cases_df = pd.DataFrame()

    if system_results_path:
        system_results = load_system_results(system_results_path)
        compare_summary_df = build_compare_summary_df(teacher_summary_df, system_results)
        question_metrics_df = build_question_metrics_df(compare_summary_df)
        worst_cases_df = build_worst_cases_df(compare_summary_df)
        if also_export_csv:
            localize_teacher_summary_df(compare_summary_df).to_csv(
                output_dir / "validation_compare_summary.csv", index=False, encoding="utf-8-sig"
            )
            localize_question_metrics_df(question_metrics_df).to_csv(
                output_dir / "validation_question_metrics.csv", index=False, encoding="utf-8-sig"
            )
            localize_worst_cases_df(worst_cases_df).to_csv(
                output_dir / "validation_worst_cases.csv", index=False, encoding="utf-8-sig"
            )

    if also_export_csv:
        teacher_summary_export_df.to_csv(output_dir / "validation_teacher_summary.csv", index=False, encoding="utf-8-sig")
        teacher_question_export_df.to_csv(
            output_dir / "validation_teacher_question_scores.csv", index=False, encoding="utf-8-sig"
        )

    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        overview_export_df.to_excel(writer, index=False, sheet_name="概览")
        teacher_summary_export_df.to_excel(writer, index=False, sheet_name="教师总表")
        teacher_question_export_df.to_excel(writer, index=False, sheet_name="教师逐题")
        if not compare_summary_df.empty:
            build_compare_export_df(compare_summary_df).to_excel(writer, index=False, sheet_name="评分对比")
        if not question_metrics_df.empty:
            localize_question_metrics_df(question_metrics_df).to_excel(writer, index=False, sheet_name="题目统计")
        if not worst_cases_df.empty:
            localize_worst_cases_df(worst_cases_df).to_excel(writer, index=False, sheet_name="高误差样本")

    logger.info("Exported validation report to %s", workbook_path)
    return workbook_path


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    template_config = load_template_config(args.template_config)
    workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    split_file = args.split_file.resolve()
    output_dir = args.output_dir.resolve()
    system_results = args.system_results.resolve() if args.system_results else None
    export_validation_report(workspace, split_file, output_dir, system_results, also_export_csv=args.also_export_csv)


if __name__ == "__main__":
    main()
