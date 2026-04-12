from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

COMMON_EXPORTS: dict[str, Any] = {}
CRITERION_TOPIC_MAP = {
    "req_usecase_spec_quality": "req_usecase",
    "req_process_expression": "req_flow",
    "hld_usecase_sequence_alignment": "hld_sequence",
    "lld_ui_alignment": "ui",
    "lld_class_alignment": "class",
    "lld_api_alignment": "api",
    "lld_database_alignment": "database",
    "lld_method_flow_feasibility": "method_flow",
    "individual_contribution_alignment": "contribution",
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


def _bootstrap_common() -> None:
    if COMMON_EXPORTS:
        return

    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    try:
        from common import (  # type: ignore
            PRACTICUM_ROOT,
            batch_score_module,
            ensure_workspace_dirs,
            load_config,
            model_name,
            now_iso,
            render_ir_for_scoring,
            rubric_path,
            worker_count,
            workspace_path,
        )
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "unknown"
        expected_venv = Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "python.exe"
        message = "\n".join(
            [
                f"启动失败：缺少 Python 依赖模块 `{missing_module}`。",
                f"当前解释器：{sys.executable}",
                f"推荐解释器：{expected_venv}",
                "如果你是在 IDE 里点运行按钮，请把工作区解释器切换到项目 .venv。",
                "如果你是在 PowerShell 里运行，请优先使用：",
                r".\.venv\Scripts\python.exe .\software-project-practicum\scripts\batch_score_reports.py",
                "如果必须使用当前解释器，请先安装依赖，例如：",
                f"{sys.executable} -m pip install pyyaml pandas openpyxl",
            ]
        )
        raise SystemExit(message) from exc

    COMMON_EXPORTS.update(
        {
            "PRACTICUM_ROOT": PRACTICUM_ROOT,
            "batch_score_module": batch_score_module,
            "ensure_workspace_dirs": ensure_workspace_dirs,
            "load_config": load_config,
            "model_name": model_name,
            "now_iso": now_iso,
            "render_ir_for_scoring": render_ir_for_scoring,
            "rubric_path": rubric_path,
            "worker_count": worker_count,
            "workspace_path": workspace_path,
        }
    )


def _common(name: str) -> Any:
    _bootstrap_common()
    return COMMON_EXPORTS[name]


def load_ir_file(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return repair_mojibake_obj(json.load(f))


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(repair_mojibake_obj(payload), f, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def build_traceability_scoring_prompt(base_module, rubric, student_id: str, content_text: str, submission_type: str) -> str:
    base_prompt = base_module.build_scoring_user_prompt(rubric, student_id, content_text, submission_type)
    extra = """

## Additional Traceability Output

Before scoring, explicitly treat template placeholder text as incomplete content rather than finished design evidence.
Examples of placeholder-like text include:
- "采用用例规约表"
- "流程图如下"
- "请在此处补充"
- other obvious template guidance, empty headings, or instructions that were not replaced with actual student content

Scoring rules for placeholder content:
- A heading without substantive body text does not count as completed coverage.
- Template guidance sentences do not count as use case specifications, method design, interface design, or database design.
- If a section only shows a template phrase and no real details, score it as missing or weak rather than completed.
- If database/interface/method sections contain off-topic template leftovers from another project, treat that as inconsistency evidence.
- Sections explicitly marked by the system as ignored placeholder sections must not be used as positive scoring evidence.
- If a criterion's relevant topic has no valid evidence left after placeholder filtering, that criterion should be scored as 0.
- Mixed sections may only be scored from their real design content, not from template headings or placeholder prose.

In addition to the required scoring fields, include a top-level JSON object named `traceability_analysis`.
This object is required for this practicum-report workflow and must contain:

{
  "extracted_requirements": ["<requirement 1>", "<requirement 2>"],
  "hld_coverage": [
    {
      "requirement": "<requirement>",
      "status": "covered|weak|incorrect|missing",
      "evidence": "<brief evidence or explanation>"
    }
  ],
  "lld_coverage": [
    {
      "requirement": "<requirement>",
      "status": "covered|weak|incorrect|missing",
      "evidence": "<brief evidence or explanation>"
    }
  ],
  "consistency_issues": ["<issue 1>"],
  "uncovered_requirements": ["<requirement that was not implemented in design>"]
}

Statuses must be one of:
- covered
- weak
- incorrect
- missing

Return JSON only.
"""
    return base_prompt + extra


def build_comment_repair_instruction(previous_text: str, issues: list[str]) -> str:
    issue_text = "; ".join(issue for issue in issues if issue.strip()) or "invalid_json"
    return "\n".join(
        [
            "上一条评论响应未通过解析或校验，请重新生成。",
            "你必须只返回一个合法 JSON 对象，不要使用 Markdown，不要使用代码块，不要添加任何解释文字。",
            'JSON 必须包含四个字符串字段：strengths, weaknesses, suggestions, full_text。',
            f"上次问题：{issue_text}",
            f"上次响应原文：{previous_text[:1200]}",
        ]
    )


def normalize_comment_payload(payload: dict[str, Any]) -> dict[str, str]:
    strengths = str(payload.get("strengths", "") or "").strip()
    weaknesses = str(payload.get("weaknesses", "") or "").strip()
    suggestions = str(payload.get("suggestions", "") or "").strip()
    full_text = str(payload.get("full_text", "") or "").strip()
    if not full_text:
        full_text = " ".join(part for part in [strengths, weaknesses, suggestions] if part).strip()
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "full_text": full_text,
    }


def build_fallback_comment(score_json: dict[str, Any]) -> dict[str, str]:
    dimensions = list(score_json.get("dimension_scores", []) or [])
    high_dims = sorted(dimensions, key=lambda item: float(item.get("score", 0) or 0), reverse=True)[:2]
    low_dims = sorted(dimensions, key=lambda item: float(item.get("score", 0) or 0))[:2]

    strength_names = [str(item.get("criterion_name", item.get("criterion_id", ""))).strip() for item in high_dims]
    weakness_names = [str(item.get("criterion_name", item.get("criterion_id", ""))).strip() for item in low_dims]
    improvements = [
        str(item.get("improvement", "")).strip()
        for item in low_dims
        if str(item.get("improvement", "")).strip()
    ]

    strengths = "优点：" + ("、".join(name for name in strength_names if name) if strength_names else "文档中仍能看到部分需求到设计的承接关系。")
    weaknesses = "不足：" + ("、".join(name for name in weakness_names if name) if weakness_names else "当前结果显示仍存在若干一致性或展开不足的问题。")
    suggestions = "建议：" + ("；".join(improvements) if improvements else "优先补齐需求到概要、详细设计的追踪关系，并完善关键章节正文。")
    full_text = " ".join([strengths, weaknesses, suggestions]).strip()
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "full_text": full_text,
    }


def apply_placeholder_enforcement(
    score_json: dict[str, Any],
    ir: dict[str, Any],
    rubric,
    base_module,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    topic_stats = dict(ir.get("metadata", {}).get("topic_stats", {}) or {})
    dimensions = list(score_json.get("dimension_scores", []) or [])
    enforced: list[dict[str, Any]] = []
    adjusted_dimensions: list[dict[str, Any]] = []

    for dim in dimensions:
        adjusted = dict(dim)
        criterion_id = str(adjusted.get("criterion_id", "")).strip()
        topic = CRITERION_TOPIC_MAP.get(criterion_id)
        if topic:
            counters = dict(topic_stats.get(topic, {}) or {})
            valid_count = int(counters.get("valid_count", 0) or 0)
            placeholder_only_count = int(counters.get("placeholder_only_count", 0) or 0)
            mixed_count = int(counters.get("mixed_count", 0) or 0)
            if valid_count == 0 and placeholder_only_count > 0 and mixed_count == 0:
                original_score = float(adjusted.get("score", 0) or 0)
                if original_score != 0:
                    adjusted["score"] = 0
                    improvement = str(adjusted.get("improvement", "")).strip()
                    note = "该维度只有模板占位证据，没有有效正文，系统已强制记 0 分。"
                    adjusted["improvement"] = f"{improvement} {note}".strip() if improvement else note
                    enforced.append(
                        {
                            "criterion_id": criterion_id,
                            "topic": topic,
                            "original_score": original_score,
                            "adjusted_score": 0,
                            "reason": f"valid_count=0, placeholder_only_count={placeholder_only_count}, mixed_count={mixed_count}",
                        }
                    )
        adjusted_dimensions.append(adjusted)

    adjusted_score_json = dict(score_json)
    adjusted_score_json["dimension_scores"] = adjusted_dimensions
    raw_total_score = round(sum(float(dim.get("score", 0) or 0) for dim in adjusted_dimensions), 2)
    max_total_score = float(
        adjusted_score_json.get("max_total_score", rubric.max_total_score) or rubric.max_total_score or 0.0
    )
    adjusted_score_json["raw_total_score"] = raw_total_score
    adjusted_score_json["max_total_score"] = max_total_score
    adjusted_score_json["percentile_score"] = base_module.compute_percentile_from_raw(raw_total_score, max_total_score)
    adjusted_score_json["grade"] = base_module.classify_grade(raw_total_score, rubric.thresholds)
    return adjusted_score_json, enforced


async def generate_comment_with_fallback(base_module, model: str, rubric, score_json: dict[str, Any], semaphore: asyncio.Semaphore, student_id: str) -> tuple[dict[str, str], str, str, int, int, int]:
    comment_system = base_module.build_comment_system_prompt(rubric)
    base_user_content = base_module.build_comment_user_prompt(rubric, score_json)
    user_content = base_user_content
    total_input_tokens = 0
    total_output_tokens = 0
    attempts = 0
    last_error = ""

    for attempt in range(1, 3):
        attempts = attempt
        async with semaphore:
            comment_response = await asyncio.to_thread(
                base_module._call_with_retry,  # noqa: SLF001
                model=model,
                system_prompt=comment_system,
                user_content=user_content,
                context=f"comment {student_id} attempt {attempt}",
            )
        total_input_tokens += int(comment_response.get("_input_tokens", 0))
        total_output_tokens += int(comment_response.get("_output_tokens", 0))
        try:
            parsed = base_module.extract_json_from_response(comment_response["_text"])
            issues = base_module.validate_comment_response(parsed)
            if not issues:
                status = "ok" if attempt == 1 else "repaired"
                return normalize_comment_payload(parsed), status, "", attempts, total_input_tokens, total_output_tokens
            last_error = "; ".join(issues)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

        logger.warning("Comment generation issues for %s on attempt %d: %s", student_id, attempt, last_error)
        if attempt == 1:
            repair_instruction = build_comment_repair_instruction(comment_response.get("_text", ""), [last_error])
            user_content = list(base_user_content) + [{"type": "text", "text": repair_instruction}]

    fallback_comment = build_fallback_comment(score_json)
    return fallback_comment, "fallback", last_error, attempts, total_input_tokens, total_output_tokens


def determine_review_flag(
    grade_value: str,
    overall_confidence: float,
    gate_status: dict[str, Any],
    evidence_quality: str,
    traceability_analysis: dict[str, Any],
    placeholder_count: int,
    comment_status: str,
    placeholder_forced_zero_count: int,
) -> str:
    flags: list[str] = []
    if not gate_status.get("all_passed", True):
        flags.append("missing_core_documents")
    if grade_value in {"review", "reject"}:
        flags.append("manual_review")
    if overall_confidence < 0.7:
        flags.append("low_confidence")
    if evidence_quality != "complete":
        flags.append("partial_evidence")

    uncovered_count = len(list(traceability_analysis.get("uncovered_requirements", []) or []))
    issue_count = len(list(traceability_analysis.get("consistency_issues", []) or []))
    if uncovered_count >= 4:
        flags.append("major_traceability_gaps")
    if issue_count >= 4:
        flags.append("consistency_risk")
    if placeholder_count >= 3:
        flags.append("template_placeholder_heavy")
    if placeholder_forced_zero_count > 0:
        flags.append("placeholder_zero_forced")
    if comment_status == "repaired":
        flags.append("comment_repair_used")
    if comment_status == "fallback":
        flags.append("comment_fallback_used")

    unique_flags: list[str] = []
    for flag in flags:
        if flag not in unique_flags:
            unique_flags.append(flag)
    return "none" if not unique_flags else ",".join(unique_flags)


def build_comment_repair_instruction(previous_text: str, issues: list[str]) -> str:
    issue_text = "; ".join(issue for issue in issues if issue.strip()) or "invalid_json"
    return "\n".join(
        [
            "上一条评语响应未通过解析或校验，请重新生成。",
            "你必须只返回一个合法 JSON 对象，不要使用 Markdown，不要使用代码块，也不要添加任何解释文字。",
            "JSON 必须包含四个字符串字段：strengths, weaknesses, suggestions, full_text。",
            f"上次问题：{issue_text}",
            f"上次响应原文：{previous_text[:1200]}",
        ]
    )


def build_fallback_comment(score_json: dict[str, Any]) -> dict[str, str]:
    dimensions = list(score_json.get("dimension_scores", []) or [])
    high_dims = sorted(dimensions, key=lambda item: float(item.get("score", 0) or 0), reverse=True)[:2]
    low_dims = sorted(dimensions, key=lambda item: float(item.get("score", 0) or 0))[:2]

    strength_names = [str(item.get("criterion_name", item.get("criterion_id", ""))).strip() for item in high_dims]
    weakness_names = [str(item.get("criterion_name", item.get("criterion_id", ""))).strip() for item in low_dims]
    improvements = [
        str(item.get("improvement", "")).strip()
        for item in low_dims
        if str(item.get("improvement", "")).strip()
    ]

    strengths = "优点：" + ("。".join(name for name in strength_names if name) if strength_names else "文档中仍能看出部分需求到设计的承接关系。")
    weaknesses = "不足：" + ("。".join(name for name in weakness_names if name) if weakness_names else "当前结果显示仍存在若干一致性或展开不足的问题。")
    suggestions = "建议：" + ("；".join(improvements) if improvements else "优先补齐需求到概要、详细设计的追踪关系，并完善关键章节正文。")
    full_text = " ".join([strengths, weaknesses, suggestions]).strip()
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "full_text": full_text,
    }


async def score_one_submission(base_module, model: str, rubric, ir: dict[str, Any], semaphore: asyncio.Semaphore) -> dict[str, Any]:
    student_id = ir.get("student_id", "unknown")
    start_ms = time.monotonic_ns() // 1_000_000
    gate_status = {
        "all_passed": all(g.get("passed", True) for g in ir.get("gate_results", [])),
        "details": list(ir.get("gate_results", [])),
    }

    content_text = _common("render_ir_for_scoring")(ir)
    prompt = build_traceability_scoring_prompt(base_module, rubric, student_id, content_text, ir.get("submission_type", "text"))
    user_content = [{"type": "text", "text": prompt}]

    scoring_data = await base_module._score_submission_json(  # noqa: SLF001
        model=model,
        rubric=rubric,
        semaphore=semaphore,
        user_content=user_content,
        context=f"score {student_id}",
    )
    score_json = scoring_data["score_json"]
    score_json, placeholder_enforcement = apply_placeholder_enforcement(
        score_json=score_json,
        ir=ir,
        rubric=rubric,
        base_module=base_module,
    )

    comment_json, comment_status, comment_error, comment_attempts, comment_input_tokens, comment_output_tokens = await generate_comment_with_fallback(
        base_module=base_module,
        model=model,
        rubric=rubric,
        score_json=score_json,
        semaphore=semaphore,
        student_id=student_id,
    )

    raw_total_score = float(score_json.get("raw_total_score", 0.0) or 0.0)
    max_total_score = float(score_json.get("max_total_score", rubric.max_total_score) or rubric.max_total_score or 0.0)
    overall_confidence = float(score_json.get("overall_confidence", 0.0) or 0.0)
    percentile_score = int(score_json.get("percentile_score", base_module.compute_percentile_from_raw(raw_total_score, max_total_score)) or 0)
    grade_value = str(score_json.get("grade", base_module.classify_grade(raw_total_score, rubric.thresholds)) or "")
    traceability_analysis = score_json.get("traceability_analysis", {}) or {}
    placeholder_count = int(ir.get("metadata", {}).get("placeholder_count", 0) or 0)
    placeholder_forced_zero_count = len(placeholder_enforcement)
    placeholder_sections_summary: list[str] = []
    for document in ir.get("content", {}).get("documents", []) or []:
        for item in list(document.get("metadata", {}).get("placeholder_sections", []) or [])[:8]:
            heading = str(item.get("heading", "")).strip() or "未命名章节"
            topic = str(item.get("topic", "")).strip()
            section_type = str(item.get("section_type", "")).strip()
            signals = ",".join(str(signal).strip() for signal in item.get("signals", []) if str(signal).strip())
            summary = heading
            if topic:
                summary += f" [{topic}]"
            if section_type:
                summary += f" ({section_type})"
            if signals:
                summary += f" - {signals}"
            placeholder_sections_summary.append(summary)

    final_record = {
        "student_id": student_id,
        "rubric_id": rubric.id,
        "scored_at": _common("now_iso")(),
        "gate_status": gate_status,
        "dimension_scores": score_json.get("dimension_scores", []),
        "raw_total_score": raw_total_score,
        "max_total_score": max_total_score,
        "percentile_score": percentile_score,
        "grade": grade_value,
        "overall_confidence": overall_confidence,
        "review_flag": determine_review_flag(
            grade_value=grade_value,
            overall_confidence=overall_confidence,
            gate_status=gate_status,
            evidence_quality=ir.get("content", {}).get("evidence_quality", "complete"),
            traceability_analysis=traceability_analysis,
            placeholder_count=placeholder_count,
            comment_status=comment_status,
            placeholder_forced_zero_count=placeholder_forced_zero_count,
        ),
        "comment": comment_json,
        "traceability_analysis": traceability_analysis,
        "metadata": {
            "source_files": ir.get("source_files", []),
            "document_roles_present": ir.get("metadata", {}).get("document_roles_present", []),
            "placeholder_count": placeholder_count,
            "placeholder_sections_summary": placeholder_sections_summary,
            "placeholder_enforcement": placeholder_enforcement,
            "placeholder_forced_zero_count": placeholder_forced_zero_count,
            "comment_status": comment_status,
            "comment_error": comment_error,
            "comment_attempts": comment_attempts,
            "validation_errors": list(scoring_data.get("validation_errors", [])),
            "duration_ms": time.monotonic_ns() // 1_000_000 - start_ms,
            "input_tokens": int(scoring_data.get("input_tokens", 0)) + comment_input_tokens,
            "output_tokens": int(scoring_data.get("output_tokens", 0)) + comment_output_tokens,
        },
    }
    return final_record


def save_progress(path: Path, payload: dict[str, Any]) -> None:
    save_json_atomic(path, payload)


async def run_batch(config_path: Path | None = None) -> None:
    config = _common("load_config")(config_path)
    effective_config = (config_path or _common("PRACTICUM_ROOT") / "grader-config.yaml").resolve()
    os.environ["GRADER_CONFIG_PATH"] = str(effective_config)
    workspace = _common("workspace_path")(config)
    _common("ensure_workspace_dirs")(workspace)

    rubric_file = _common("rubric_path")(config)
    base_module = _common("batch_score_module")()
    if hasattr(base_module, "_set_runtime_config_path"):
        base_module._set_runtime_config_path(effective_config)  # noqa: SLF001
    rubric = base_module.load_rubric(rubric_file)

    model = os.environ.get("SCORING_MODEL", "").strip() or _common("model_name")(config)
    ir_dir = workspace / "ir"
    scores_dir = workspace / "scores"
    progress_path = workspace / "progress.json"
    ir_files = sorted(ir_dir.glob("*.json"))
    if not ir_files:
        logger.warning("No IR files found in %s", ir_dir)
        return

    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or str(config.get("openai", {}).get("api_key", "")).strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Configure it in the environment or software-project-practicum/grader-config.yaml")

    semaphore = asyncio.Semaphore(_common("worker_count")(config))
    progress = {
        "batch_id": workspace.name,
        "rubric_id": rubric.id,
        "mode": "real-time",
        "started_at": _common("now_iso")(),
        "last_updated": _common("now_iso")(),
        "total": len(ir_files),
        "completed": 0,
        "failed": 0,
        "pending": len(ir_files),
        "completed_ids": [],
        "failed_ids": [],
        "pending_ids": [path.stem for path in ir_files],
    }
    save_progress(progress_path, progress)

    for index, ir_path in enumerate(ir_files, start=1):
        student_id = ir_path.stem
        logger.info("[%d/%d] Scoring %s", index, len(ir_files), student_id)
        try:
            ir = load_ir_file(ir_path)
            error_type = str(ir.get("metadata", {}).get("error_type", "")).strip()
            if error_type:
                raise RuntimeError(
                    f"preprocessing_error:{error_type}: {ir.get('metadata', {}).get('error_message', '')}"
                )
            result = await score_one_submission(base_module, model, rubric, ir, semaphore)
            save_json_atomic(scores_dir / f"{student_id}.json", result)
            progress["completed_ids"].append(student_id)
            progress["completed"] = len(progress["completed_ids"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to score %s: %s", student_id, exc)
            progress["failed_ids"].append({"id": student_id, "error": str(exc)})
            progress["failed"] = len(progress["failed_ids"])
        finally:
            progress["pending_ids"] = [item for item in progress["pending_ids"] if item != student_id]
            progress["pending"] = len(progress["pending_ids"])
            progress["last_updated"] = _common("now_iso")()
            save_progress(progress_path, progress)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score practicum-report IR files against the traceability rubric.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to software-project-practicum/grader-config.yaml",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    _bootstrap_common()
    asyncio.run(run_batch(args.config))


if __name__ == "__main__":
    main()
