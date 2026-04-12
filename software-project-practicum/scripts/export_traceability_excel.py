from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from common import ensure_workspace_dirs, load_config, now_iso, workspace_path

logger = logging.getLogger(__name__)

GRADE_LABELS = {
    "accept": "通过",
    "review": "待复核",
    "reject": "不通过",
}

MOJIBAKE_HINT_CHARS = "闇鍙璇鐢缁鏁鏄姒璁鏍绗鎺鍥琛鍚浣绫€"


def looks_like_mojibake(text: str) -> bool:
    if not text:
        return False
    if any(token in text for token in ("€", "鈥", "锛", "銆", "鏈", "闇€", "璇︾粏", "鐧诲綍")):
        return True
    return sum(text.count(ch) for ch in MOJIBAKE_HINT_CHARS) >= 2


def _mojibake_score(text: str) -> int:
    if not text:
        return -10_000
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    hint_penalty = sum(text.count(ch) for ch in MOJIBAKE_HINT_CHARS) * 4
    symbol_penalty = sum(text.count(ch) for ch in "€鈥锛銆�") * 6
    return cjk_count - hint_penalty - symbol_penalty


def repair_mojibake_text(text: str) -> str:
    if not isinstance(text, str) or not looks_like_mojibake(text):
        return text

    best = text
    best_score = _mojibake_score(text)
    for codec in ("gbk", "gb18030"):
        try:
            repaired = text.encode(codec, errors="ignore").decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        repaired_score = _mojibake_score(repaired)
        if repaired and repaired_score > best_score:
            best = repaired
            best_score = repaired_score
    return best


def repair_mojibake_obj(value: Any) -> Any:
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_mojibake_obj(item) for item in value]
    if isinstance(value, dict):
        return {
            repair_mojibake_text(key) if isinstance(key, str) else key: repair_mojibake_obj(item)
            for key, item in value.items()
        }
    return value


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return {
            row.get("anon_id", "").strip(): {
                "student_number": repair_mojibake_text(row.get("student_number", "").strip()),
                "name": repair_mojibake_text(row.get("name", "").strip()),
            }
            for row in reader
            if row.get("anon_id", "").strip()
        }


def load_scores(scores_dir: Path) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for path in sorted(scores_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            scores.append(repair_mojibake_obj(json.load(f)))
    return scores


def _coverage_summary(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        requirement = str(item.get("requirement", "")).strip()
        status = str(item.get("status", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        line = f"{requirement} [{status}]".strip()
        if evidence:
            line += f" - {evidence}"
        parts.append(line)
    return "\n".join(part for part in parts if part.strip())


def _placeholder_enforcement_summary(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        criterion_id = str(item.get("criterion_id", "")).strip()
        topic = str(item.get("topic", "")).strip()
        original_score = item.get("original_score", "")
        adjusted_score = item.get("adjusted_score", "")
        reason = str(item.get("reason", "")).strip()
        line = criterion_id
        if topic:
            line += f" [{topic}]"
        if original_score != "":
            line += f" {original_score}->{adjusted_score}"
        if reason:
            line += f" - {reason}"
        parts.append(line)
    return "\n".join(part for part in parts if part.strip())


def build_grade_table(scores: list[dict[str, Any]], mapping: dict[str, dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, score in enumerate(scores, start=1):
        student_id = score.get("student_id", f"unknown-{index}")
        student_info = mapping.get(student_id, {})
        traceability = score.get("traceability_analysis", {}) or {}
        uncovered_requirements = list(traceability.get("uncovered_requirements", []) or [])
        consistency_issues = list(traceability.get("consistency_issues", []) or [])
        metadata = score.get("metadata", {}) or {}
        placeholder_enforcement = list(metadata.get("placeholder_enforcement", []) or [])

        row: dict[str, Any] = {
            "序号": index,
            "学号": student_info.get("student_number", student_id),
            "姓名": student_info.get("name", ""),
            "原始总分": score.get("raw_total_score", 0.0),
            "满分": score.get("max_total_score", 0.0),
            "百分制": score.get("percentile_score", 0),
            "等级": GRADE_LABELS.get(str(score.get("grade", "")), str(score.get("grade", ""))),
            "置信度": score.get("overall_confidence", 0.0),
            "复核标记": score.get("review_flag", ""),
            "模板占位数": metadata.get("placeholder_count", 0),
            "模板占位强制归零项数": metadata.get("placeholder_forced_zero_count", 0),
            "模板占位强制归零明细": _placeholder_enforcement_summary(placeholder_enforcement),
            "未覆盖需求数": len(uncovered_requirements),
            "一致性问题数": len(consistency_issues),
            "评语摘要": str(score.get("comment", {}).get("full_text", ""))[:240],
        }
        for dim in score.get("dimension_scores", []):
            dim_name = dim.get("criterion_name", dim.get("criterion_id", ""))
            row[str(dim_name)] = dim.get("score", 0)
        rows.append(row)
    return pd.DataFrame(rows)


def build_traceability_table(scores: list[dict[str, Any]], mapping: dict[str, dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for score in scores:
        student_id = score.get("student_id", "")
        student_info = mapping.get(student_id, {})
        traceability = score.get("traceability_analysis", {}) or {}
        metadata = score.get("metadata", {}) or {}
        rows.append(
            {
                "学号": student_info.get("student_number", student_id),
                "姓名": student_info.get("name", ""),
                "抽取需求清单": "\n".join(traceability.get("extracted_requirements", []) or []),
                "概要设计覆盖状态": _coverage_summary(list(traceability.get("hld_coverage", []) or [])),
                "详细设计落地状态": _coverage_summary(list(traceability.get("lld_coverage", []) or [])),
                "一致性问题": "\n".join(traceability.get("consistency_issues", []) or []),
                "未覆盖需求": "\n".join(traceability.get("uncovered_requirements", []) or []),
                "被排除的占位章节摘要": "\n".join(metadata.get("placeholder_sections_summary", []) or []),
            }
        )
    return pd.DataFrame(rows)


def build_statistics(scores: list[dict[str, Any]], grade_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [{"指标": "总人数", "值": len(scores)}]
    if not grade_df.empty:
        rows.append({"指标": "原始总分均分", "值": round(float(grade_df["原始总分"].mean()), 2)})
        rows.append({"指标": "百分制均分", "值": round(float(grade_df["百分制"].mean()), 2)})
        rows.append({"指标": "低置信度人数", "值": int((grade_df["置信度"] < 0.6).sum())})
        rows.append({"指标": "模板占位总数", "值": int(grade_df["模板占位数"].sum())})
        rows.append({"指标": "模板占位强制归零项总数", "值": int(grade_df["模板占位强制归零项数"].sum())})
        rows.append({"指标": "未覆盖需求总数", "值": int(grade_df["未覆盖需求数"].sum())})
        rows.append({"指标": "一致性问题总数", "值": int(grade_df["一致性问题数"].sum())})
    else:
        rows.extend(
            [
                {"指标": "原始总分均分", "值": 0},
                {"指标": "百分制均分", "值": 0},
                {"指标": "低置信度人数", "值": 0},
                {"指标": "模板占位总数", "值": 0},
                {"指标": "模板占位强制归零项总数", "值": 0},
                {"指标": "未覆盖需求总数", "值": 0},
                {"指标": "一致性问题总数", "值": 0},
            ]
        )

    dim_totals: dict[str, list[float]] = {}
    for score in scores:
        for dim in score.get("dimension_scores", []):
            key = str(dim.get("criterion_name", dim.get("criterion_id", "")))
            dim_totals.setdefault(key, []).append(float(dim.get("score", 0) or 0))
    for dim_name, values in dim_totals.items():
        rows.append({"指标": f"维度均分: {dim_name}", "值": round(sum(values) / len(values), 2)})

    if not grade_df.empty:
        for forced_count, total in grade_df["模板占位强制归零项数"].value_counts().sort_index().items():
            rows.append({"指标": f"模板占位强制归零项数={forced_count}", "值": int(total)})
        for uncovered_count, total in grade_df["未覆盖需求数"].value_counts().sort_index().items():
            rows.append({"指标": f"未覆盖需求数={uncovered_count}", "值": int(total)})
        for issue_count, total in grade_df["一致性问题数"].value_counts().sort_index().items():
            rows.append({"指标": f"一致性问题数={issue_count}", "值": int(total)})
        for review_flag, total in grade_df["复核标记"].value_counts().sort_index().items():
            rows.append({"指标": f"复核标记={review_flag}", "值": int(total)})

    return pd.DataFrame(rows)


def write_excel(output_path: Path, grade_df: pd.DataFrame, trace_df: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        grade_df.to_excel(writer, sheet_name="成绩表", index=False)
        trace_df.to_excel(writer, sheet_name="追踪明细", index=False)
        stats_df.to_excel(writer, sheet_name="统计表", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export practicum scoring results to Excel.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to software-project-practicum/grader-config.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output .xlsx path. Defaults to workspace/reports/traceability-grades-<timestamp>.xlsx",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config = load_config(args.config)
    workspace = workspace_path(config)
    ensure_workspace_dirs(workspace)

    mapping = load_mapping(workspace / "student-mapping.csv")
    scores = load_scores(workspace / "scores")
    if not scores:
        logger.warning("No scores found in %s", workspace / "scores")
        return

    grade_df = build_grade_table(scores, mapping)
    trace_df = build_traceability_table(scores, mapping)
    stats_df = build_statistics(scores, grade_df)

    output_path = args.output or workspace / "reports" / f"traceability-grades-{now_iso().replace(':', '').replace('-', '')[:15]}.xlsx"
    write_excel(output_path, grade_df, trace_df, stats_df)
    logger.info("Wrote Excel report to %s", output_path)


if __name__ == "__main__":
    main()
