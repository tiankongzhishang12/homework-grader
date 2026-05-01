from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from common import ensure_phase1_dirs, load_template_config, phase1_workspace_path

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export phase1 answer-card parsed results to Excel.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    return parser.parse_args()


def load_parsed_results(parsed_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(parsed_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            results.append(json.load(f))
    return results


def build_scores_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in results:
        section_scores = item.get("section_scores", {}) or {}
        question_scores = item.get("question_scores", {}) or {}
        confidence = item.get("confidence", {}) or {}
        checks = item.get("checks", {}) or {}
        rows.append(
            {
                "paper_id": item.get("paper_id", ""),
                "学号": item.get("student_number", ""),
                "姓名": item.get("student_name", ""),
                "单选得分": section_scores.get("single_choice"),
                "判断得分": section_scores.get("true_false"),
                "填空得分": section_scores.get("fill_blank"),
                "解答题得分": section_scores.get("short_answer"),
                "综合题得分": section_scores.get("comprehensive"),
                "26题": question_scores.get("26"),
                "27题": question_scores.get("27"),
                "28题": question_scores.get("28"),
                "29题": question_scores.get("29"),
                "30题": question_scores.get("30"),
                "31题": question_scores.get("31"),
                "32题": question_scores.get("32"),
                "33题": question_scores.get("33"),
                "总分": item.get("total_score"),
                "计算总分": checks.get("computed_total"),
                "总分一致": checks.get("sum_matches_total"),
                "需要复核": item.get("needs_review"),
                "置信度": confidence.get("overall"),
                "问题": " | ".join(checks.get("issues", []) or []),
                "备注": " | ".join(item.get("notes", []) or []),
                "原图路径": item.get("source_image", ""),
            }
        )
    return pd.DataFrame(rows)


def build_statistics_dataframe(results: list[dict[str, Any]], score_df: pd.DataFrame) -> pd.DataFrame:
    stats: list[dict[str, Any]] = [{"指标": "总卷数", "值": len(results)}]
    if score_df.empty:
        return pd.DataFrame(stats)
    stats.append({"指标": "成功提取总分数", "值": int(score_df["总分"].notna().sum())})
    stats.append({"指标": "待复核卷数", "值": int(score_df["需要复核"].fillna(False).sum())})
    stats.append({"指标": "总分均分", "值": round(float(score_df["总分"].dropna().mean()), 2) if score_df["总分"].notna().any() else 0})
    stats.append({"指标": "最低总分", "值": float(score_df["总分"].dropna().min()) if score_df["总分"].notna().any() else 0})
    stats.append({"指标": "最高总分", "值": float(score_df["总分"].dropna().max()) if score_df["总分"].notna().any() else 0})
    issue_counts = score_df["问题"].value_counts()
    for issue, count in issue_counts.items():
        issue_text = str(issue).strip()
        if not issue_text:
            continue
        stats.append({"指标": f"问题数: {issue_text}", "值": int(count)})
    return pd.DataFrame(stats)


def export_phase1_results(workspace: Path) -> Path:
    dirs = ensure_phase1_dirs(workspace)
    results = load_parsed_results(dirs["parsed"])
    score_df = build_scores_dataframe(results)
    stats_df = build_statistics_dataframe(results, score_df)
    review_df = score_df[score_df["需要复核"] == True].copy() if not score_df.empty else pd.DataFrame()
    output_path = dirs["exports"] / "answer-card-scores.xlsx"
    csv_path = dirs["exports"] / "answer-card-scores.csv"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        score_df.to_excel(writer, index=False, sheet_name="scores")
        stats_df.to_excel(writer, index=False, sheet_name="stats")
        review_df.to_excel(writer, index=False, sheet_name="review")
    score_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("Exported phase1 score sheets to %s", output_path)
    return output_path


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    template_config = load_template_config(args.template_config)
    workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    export_phase1_results(workspace)


if __name__ == "__main__":
    main()
