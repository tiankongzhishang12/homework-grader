#!/usr/bin/env python3
"""Batch scoring orchestrator for the homework-grader Skill.

Scores preprocessed IR files against a Rubric using the OpenAI API.
Supports real-time mode with progress tracking, resume, anti-position-bias
randomization, and per-item error isolation.

Usage:
    python batch_score.py <workspace_dir> --rubric <rubric.yaml> \\
        [--workers 5] [--resume]

Examples:
    # Real-time mode, 5 concurrent workers
    python batch_score.py workspace/research-methods-20260315 \\
        --rubric rubric.yaml

    # Resume an interrupted batch
    python batch_score.py workspace/research-methods-20260315 \\
        --rubric rubric.yaml --resume
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import logging
import os
import random
import re
import sys
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import APITimeoutError, APIConnectionError, APIStatusError, OpenAI, RateLimitError
import yaml
from export_excel import (
    build_detail_table,
    build_grade_table,
    build_statistics,
    load_mapping,
    load_scores,
    write_excel,
)

try:
    from PIL import Image  # type: ignore
except Exception:  # noqa: BLE001
    Image = None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_WORKERS = 5
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 2.0
MAX_ATTACHED_IMAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_SCORING_ATTEMPTS = 2
SECOND_PASS_CONFIDENCE_THRESHOLD = 0.8
SECOND_PASS_MARGIN_THRESHOLD = 0.3
SECOND_PASS_TOTAL_DIFF_THRESHOLD = 0.5
SECOND_PASS_DIM_DIFF_THRESHOLD = 1
OBJECTIVE_QUESTION_TYPES = {"single_choice", "multiple_choice", "judgment", "fill_blank"}

# Pricing per million tokens (rough estimate for the default model).
INPUT_PRICE_PER_MTOK = 0.25
OUTPUT_PRICE_PER_MTOK = 2.0

_OPENAI_CLIENT: OpenAI | None = None
_PROJECT_CONFIG: dict[str, Any] | None = None
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "grader-config.yaml"
_CONFIG_PATH_OVERRIDE: Path | None = None

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RubricCriterion:
    """A single scoring dimension from the Rubric."""

    criterion_id: str
    name: str
    weight: float
    scale: list[int]
    description: str
    scoring_guidance: str
    anchors: dict[int, str]
    evidence_type: str
    question_type: str = ""
    question_range: str = ""
    max_score: int = 5
    scoring_rule: str = ""
    evidence_source: str = "text"
    answer_key: Any = None
    core_points: list[str] = field(default_factory=list)
    acceptable_alternatives: list[str] = field(default_factory=list)
    deduction_rules: list[str] = field(default_factory=list)
    full_score_conditions: list[str] = field(default_factory=list)
    partial_credit_conditions: list[str] = field(default_factory=list)
    zero_score_conditions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RubricThresholds:
    accept: float
    reject: float
    review: list[float]


@dataclass(frozen=True)
class CommentGuidelines:
    tone: str
    language: str
    length_range: list[int]
    required_sections: list[str]
    prohibited_patterns: list[str]


@dataclass(frozen=True)
class Rubric:
    """Parsed and validated Rubric."""

    id: str
    name: str
    version: float
    description: str
    instruction: str
    score_mode: str
    max_total_score: float
    criteria: list[RubricCriterion]
    thresholds: RubricThresholds
    comment_guidelines: CommentGuidelines


@dataclass
class FailedItem:
    id: str
    error: str
    attempts: int
    last_attempt: str = ""


@dataclass
class Progress:
    """Batch progress checkpoint - single source of truth for state."""

    batch_id: str
    rubric_id: str
    mode: str
    started_at: str
    last_updated: str
    total: int
    completed: int = 0
    failed: int = 0
    pending: int = 0
    completed_ids: list[str] = field(default_factory=list)
    failed_ids: list[FailedItem] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)
    processing_order: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoringResult:
    """Result from scoring a single submission."""

    student_id: str
    score_data: dict[str, Any]
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


class InvalidScoringResponseError(RuntimeError):
    """Raised when a scoring response stays invalid after repair."""


# ---------------------------------------------------------------------------
# Rubric loading and validation
# ---------------------------------------------------------------------------


def _criterion_max_score(criterion: RubricCriterion) -> int:
    if criterion.max_score:
        return int(criterion.max_score)
    if criterion.scale:
        return int(max(criterion.scale))
    return 5


def _criterion_min_score(criterion: RubricCriterion, score_mode: str) -> int:
    if score_mode == "raw":
        return 0
    if criterion.scale:
        return int(min(criterion.scale))
    return 1


def _normalize_total_score(raw_total_score: float, max_total_score: float) -> float:
    if max_total_score <= 0:
        return 1.0
    normalized = 1.0 + 4.0 * (raw_total_score / max_total_score)
    return round(max(1.0, min(5.0, normalized)), 2)


def load_rubric(path: Path) -> Rubric:
    """Load and validate a Rubric YAML file.

    Returns a validated Rubric dataclass. Raises ValueError on
    validation failure.
    """
    if not path.exists():
        raise FileNotFoundError(f"Rubric file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rubric_data = raw.get("rubric")
    if rubric_data is None:
        raise ValueError("YAML must contain a top-level 'rubric' key")

    # Required metadata
    rubric_id = rubric_data.get("id", "")
    rubric_name = rubric_data.get("name", "")
    rubric_version = rubric_data.get("version", 1.0)
    rubric_description = rubric_data.get("description", "")
    rubric_instruction = rubric_data.get("instruction", "")
    score_mode = str(rubric_data.get("score_mode", "scaled") or "scaled").strip().lower()
    if score_mode not in {"scaled", "raw"}:
        raise ValueError("Rubric score_mode must be 'scaled' or 'raw'")
    if not rubric_id:
        raise ValueError("Rubric must have a non-empty 'id'")

    # Criteria
    criteria_raw = rubric_data.get("criteria", {})
    if not criteria_raw:
        raise ValueError("Rubric must have at least one criterion")

    criteria: list[RubricCriterion] = []
    weight_sum = 0.0
    for cid, cdata in criteria_raw.items():
        weight = float(cdata.get("weight", 1.0 if score_mode == "raw" else 0.0))
        weight_sum += weight
        max_score = int(cdata.get("max_score", max(cdata.get("scale", [5]))))
        scale = [int(s) for s in cdata.get("scale", ([1, 2, 3, 4, 5] if score_mode == "scaled" else list(range(0, max_score + 1))))]
        anchors = {int(k): str(v) for k, v in cdata.get("anchors", {}).items()}

        if score_mode == "scaled":
            missing_anchors = [s for s in scale if s not in anchors]
            if missing_anchors:
                raise ValueError(
                    f"Criterion '{cid}': missing anchors for scale values {missing_anchors}"
                )
        elif max_score <= 0:
            raise ValueError(f"Criterion '{cid}': max_score must be > 0 in raw mode")

        criteria.append(
            RubricCriterion(
                criterion_id=cid,
                name=cdata.get("name", cid),
                weight=weight,
                scale=scale,
                description=cdata.get("description", ""),
                scoring_guidance=cdata.get("scoring_guidance", ""),
                anchors=anchors,
                evidence_type=cdata.get("evidence_type", "observation"),
                question_type=str(cdata.get("question_type", "")),
                question_range=str(cdata.get("question_range", "")),
                max_score=max_score,
                scoring_rule=str(cdata.get("scoring_rule", "")),
                evidence_source=str(cdata.get("evidence_source", "text")),
                answer_key=cdata.get("answer_key"),
                core_points=[str(v) for v in cdata.get("core_points", [])],
                acceptable_alternatives=[str(v) for v in cdata.get("acceptable_alternatives", [])],
                deduction_rules=[str(v) for v in cdata.get("deduction_rules", [])],
                full_score_conditions=[str(v) for v in cdata.get("full_score_conditions", [])],
                partial_credit_conditions=[str(v) for v in cdata.get("partial_credit_conditions", [])],
                zero_score_conditions=[str(v) for v in cdata.get("zero_score_conditions", [])],
            )
        )

    # Validate weights sum
    if score_mode == "scaled" and abs(weight_sum - 1.0) > 0.001:
        raise ValueError(
            f"Criteria weights must sum to 1.0 (got {weight_sum:.4f})"
        )
    max_total_score = float(rubric_data.get("max_total_score", 0.0) or 0.0)
    if score_mode == "raw":
        inferred_total = float(sum(_criterion_max_score(c) for c in criteria))
        if max_total_score <= 0:
            max_total_score = inferred_total

    # Thresholds
    thresholds_raw = rubric_data.get("thresholds", {})
    thresholds = RubricThresholds(
        accept=thresholds_raw.get("accept", 3.0),
        reject=thresholds_raw.get("reject", 1.5),
        review=thresholds_raw.get("review", [1.5, 3.0]),
    )
    if thresholds.accept <= thresholds.reject:
        raise ValueError("thresholds.accept must be greater than thresholds.reject")

    # Comment guidelines
    cg_raw = rubric_data.get("comment_guidelines", {})
    comment_guidelines = CommentGuidelines(
        tone=cg_raw.get("tone", "constructive, specific"),
        language=cg_raw.get("language", "zh-CN"),
        length_range=cg_raw.get("length_range", [200, 400]),
        required_sections=cg_raw.get(
            "required_sections", ["strengths", "weaknesses", "suggestions"]
        ),
        prohibited_patterns=cg_raw.get("prohibited_patterns", []),
    )

    logger.info(
        "Rubric loaded: %s (v%.1f) - %d criteria",
        rubric_id,
        rubric_version,
        len(criteria),
    )
    return Rubric(
        id=rubric_id,
        name=rubric_name or rubric_id,
        version=rubric_version,
        description=rubric_description,
        instruction=rubric_instruction,
        score_mode=score_mode,
        max_total_score=max_total_score,
        criteria=criteria,
        thresholds=thresholds,
        comment_guidelines=comment_guidelines,
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SCORING_SYSTEM_PROMPT = """\
You are a meticulous homework evaluator. You score student submissions strictly \
according to the provided Rubric. You never invent criteria beyond what the \
Rubric defines.

### Anti-Bias Directives

1. **Length != Quality** - Do NOT award higher scores because a submission is \
long. A concise, well-argued answer is equal to or better than a verbose one. \
Irrelevant padding should lower the score, not raise it.

2. **Tone != Accuracy** - Do NOT assume confident or academic-sounding language \
is correct. Evaluate claims against evidence. A hedged statement backed by \
data is worth more than an assertive claim without support.

3. **Relevance filter** - For each dimension, ONLY content directly relevant \
to that dimension's criteria contributes to the score. Off-topic elaboration \
earns ZERO credit.

4. **Evidence before score** - For every dimension, you MUST first quote or \
describe evidence from the submission, THEN reason about which anchor it \
matches, THEN assign the score. Reversing this order is forbidden.

5. **Independent dimensions** - Score each dimension on its own merits. A high \
score on one dimension must not inflate another."""

COMMENT_SYSTEM_PROMPT_TEMPLATE = """\
You are a constructive academic mentor writing feedback for a student's \
homework submission. Your comments must be specific, evidence-based, and \
actionable. You write in {language}.

### Rules

1. **Three required sections**: strengths, weaknesses, suggestions.
2. **No vague praise** - Every positive remark must cite a concrete element \
from the work.
3. **No vague criticism** - Every critique must name the exact problem and \
where it occurs.
4. **Actionable suggestions** - Each suggestion must be something the student \
can concretely do in their next assignment.
5. **Length**: {min_length}-{max_length} characters.
6. **Tone**: {tone}
7. **Prohibited patterns**: {prohibited}"""


def build_scoring_user_prompt(
    rubric: Rubric,
    student_id: str,
    submission_content: str,
    submission_type: str,
) -> str:
    """Build the user prompt for scoring a single submission."""
    rubric_metadata = []
    if rubric.description:
        rubric_metadata.append(f"**Rubric Description**: {rubric.description}")
    if rubric.instruction:
        rubric_metadata.append(
            f"**Assignment Instruction**:\n{rubric.instruction}"
        )
    rubric_metadata_text = "\n\n".join(rubric_metadata)

    dimensions_text = ""
    if rubric.score_mode == "raw":
        for c in rubric.criteria:
            answer_key_text = json.dumps(c.answer_key, ensure_ascii=False, indent=2) if c.answer_key is not None else '"<fill from standard answer>"'
            sections: list[str] = [
                f"#### {c.name} (max score: {c.max_score})",
                f"**Criterion ID**: {c.criterion_id}",
            ]
            if c.question_type:
                sections.append(f"**Question Type**: {c.question_type}")
            if c.question_range:
                sections.append(f"**Question Range**: {c.question_range}")
            sections.extend(
                [
                    f"**Description**: {c.description}",
                    f"**Scoring Guidance**: {c.scoring_guidance}",
                    f"**Scoring Rule**: {c.scoring_rule or 'Use the criterion-specific rules below.'}",
                    f"**Evidence type**: {c.evidence_type}",
                    f"**Evidence source**: {c.evidence_source}",
                    f"**Answer Key / Reference Basis**:\n```json\n{answer_key_text}\n```",
                ]
            )
            if c.core_points:
                sections.append("**Core Points**:\n" + "\n".join(f"- {item}" for item in c.core_points))
            if c.acceptable_alternatives:
                sections.append("**Acceptable Alternatives**:\n" + "\n".join(f"- {item}" for item in c.acceptable_alternatives))
            if c.full_score_conditions:
                sections.append("**Full Score Conditions**:\n" + "\n".join(f"- {item}" for item in c.full_score_conditions))
            if c.partial_credit_conditions:
                sections.append("**Partial Credit Conditions**:\n" + "\n".join(f"- {item}" for item in c.partial_credit_conditions))
            if c.zero_score_conditions:
                sections.append("**Zero Score Conditions**:\n" + "\n".join(f"- {item}" for item in c.zero_score_conditions))
            if c.deduction_rules:
                sections.append("**Deduction Rules**:\n" + "\n".join(f"- {item}" for item in c.deduction_rules))
            dimensions_text += "\n\n" + "\n\n".join(sections) + "\n"
        dim_json_example = json.dumps(
            {
                "criterion_id": "<criterion key>",
                "criterion_name": "<criterion name>",
                "weight": 1.0,
                "score": 3,
                "evidence": "<quoted text or observation>",
                "reasoning": "<how the answer was scored against the criterion-specific rules>",
                "matched_core_points": ["<matched point 1>"],
                "accepted_alternative_reasoning": "<why a non-standard but correct approach still receives credit>",
                "missing_points": ["<missing point 1>"],
                "logic_issues": ["<logic issue or empty list>"],
                "improvement": "<specific suggestion>",
                "confidence": 0.82,
            },
            ensure_ascii=False,
            indent=6,
        )
    else:
        for c in rubric.criteria:
            anchor_rows = "\n".join(
                f"| {score} | {c.anchors[score]} |"
                for score in sorted(c.anchors, reverse=True)
            )
            dimensions_text += f"""
#### {c.name} (weight: {c.weight})

**Criterion ID**: {c.criterion_id}

**Description**: {c.description}
**Scoring Guidance**: {c.scoring_guidance}

| Score | Anchor |
|-------|--------|
{anchor_rows}

**Evidence type**: {c.evidence_type}
"""
        dim_json_example = json.dumps(
            {
                "criterion_id": "<criterion key>",
                "criterion_name": "<criterion name>",
                "weight": 0.0,
                "score": 4,
                "evidence": "<quoted text or observation>",
                "reasoning": "<concise rubric-based rationale>",
                "improvement": "<specific suggestion>",
                "confidence": 0.82,
            },
            ensure_ascii=False,
            indent=6,
        )

    scoring_instructions = """Use every relevant evidence block in the submission. If there is an
Images / Diagrams section, you must inspect it for diagram-related criteria.
Do not give credit for required artifacts that are absent or not supported by
the available evidence.

For **each** dimension listed above, produce the following in strict order:

1. **Evidence** - Quote the student's own words (if evidence_type = quote) or describe your observation (if evidence_type = observation / metric). If no relevant content exists, state "No relevant evidence found."
2. **Reasoning** - Compare the evidence against anchor descriptions. Explain which anchor level it matches and why. Note any borderline considerations.
3. **Score** - An integer from 1 to 5.
4. **Improvement** - One specific, actionable suggestion the student could follow next time.
5. **Confidence** - A float from 0.0 to 1.0 indicating how confident you are in this score.

After scoring all dimensions:

6. **Weighted Total** - Calculate: sum(weight * score) rounded to 2 decimal places.
7. **Overall Confidence** - The mean of per-dimension confidence values, rounded to 2 decimal places."""

    output_format = f"""{{
  "student_id": "{student_id}",
  "rubric_id": "{rubric.id}",
  "dimension_scores": [
    {dim_json_example}
  ],
  "weighted_total": <float>,
  "overall_confidence": <float>
}}"""

    if rubric.score_mode == "raw":
        scoring_instructions = f"""Use every relevant evidence block in the submission. If there is an
Images / Diagrams section, you must inspect it for criterion-specific evidence.
Do not give credit for required artifacts that are absent or not supported by
the available evidence.

This rubric is in **raw exam-score mode**. The standard answer is a reference
baseline, not the only acceptable wording. For short-answer and comprehensive
questions, you must allow professionally valid equivalent reasoning, equivalent
steps, and equivalent conclusions when they satisfy the question.

For objective questions:
- Follow the stated scoring rule mechanically.
- If the answer depends on gray blocks or other visual marks and the evidence is
  not reliably visible, do not guess. Score conservatively and lower confidence.

For short-answer and comprehensive questions:
- Reward correct equivalent answers even when they do not mirror the reference answer's wording.
- Base partial credit on key-point coverage plus logic quality, not on length.
- Do not mechanically deduct points just because the student's phrasing differs from the reference answer.

For **each** dimension listed above, produce the following in strict order:

1. **Evidence** - Quote or describe the specific evidence used for scoring.
2. **Reasoning** - Explain how the evidence satisfies or misses the criterion-specific rule.
3. **Score** - An integer from 0 to the criterion's max score.
4. **matched_core_points** - A JSON array of the key points the student covered.
5. **accepted_alternative_reasoning** - A short explanation of any valid alternative reasoning or state an empty string.
6. **missing_points** - A JSON array of missing key points.
7. **logic_issues** - A JSON array of logic/process problems, or an empty array.
8. **Improvement** - One specific, actionable suggestion.
9. **Confidence** - A float from 0.0 to 1.0.

After scoring all dimensions:

10. **raw_total_score** - Calculate the sum of all raw item scores.
11. **max_total_score** - Use {int(rubric.max_total_score)}.
12. **Overall Confidence** - The mean of per-dimension confidence values, rounded to 2 decimal places."""
        output_format = f"""{{
  "student_id": "{student_id}",
  "rubric_id": "{rubric.id}",
  "dimension_scores": [
    {dim_json_example}
  ],
  "raw_total_score": <float>,
  "max_total_score": {int(rubric.max_total_score)},
  "overall_confidence": <float>
}}"""

    return f"""## Rubric

**Rubric ID**: {rubric.id}
**Rubric Name**: {rubric.name}

{rubric_metadata_text}

### Dimensions
{dimensions_text}
---

## Student Submission

**Student ID**: {student_id}
**Submission type**: {submission_type}

{submission_content}

---

## Scoring Instructions

{scoring_instructions}

## Output Format

Respond with **only** the following JSON (no markdown fences, no commentary):

Use the exact criterion IDs from the Rubric for every item in dimension_scores.

{output_format}"""

def build_comment_user_prompt(
    rubric: Rubric,
    score_data: dict[str, Any],
) -> str:
    """Build the user prompt for comment generation."""
    student_id = score_data.get("student_id", "")
    weighted_total = score_data.get("weighted_total", 0.0)
    raw_total_score = score_data.get("raw_total_score")
    max_total_score = score_data.get("max_total_score", rubric.max_total_score)

    # Determine grade
    grade = str(score_data.get("grade", "")).strip()
    if not grade:
        if rubric.score_mode == "raw":
            comparison_value = float(raw_total_score or 0.0)
        else:
            comparison_value = float(weighted_total or 0.0)
        if comparison_value >= rubric.thresholds.accept:
            grade = "accept"
        elif comparison_value < rubric.thresholds.reject:
            grade = "reject"
        else:
            grade = "review"

    # Per-dimension section
    dim_lines = []
    for dim in score_data.get("dimension_scores", []):
        score_denominator = 5
        if rubric.score_mode == "raw":
            matching = next(
                (criterion for criterion in rubric.criteria if criterion.criterion_id == dim.get("criterion_id")),
                None,
            )
            score_denominator = _criterion_max_score(matching) if matching is not None else dim.get("max_score", 0)
        dim_lines.append(
            f"- **{dim.get('criterion_name', '?')}** ({dim.get('weight', 0)}): "
            f"{dim.get('score', 0)}/{score_denominator}\n"
            f"  - Evidence: {dim.get('evidence', '')}\n"
            f"  - Reasoning: {dim.get('reasoning', '')}\n"
            f"  - Improvement: {dim.get('improvement', '')}"
        )
    dim_text = "\n".join(dim_lines)

    score_header = f"**Weighted Total**: {weighted_total} / 5.0"
    if rubric.score_mode == "raw":
        score_header = (
            f"**Raw Total Score**: {raw_total_score} / {max_total_score}\n"
            f"**Normalized Total**: {weighted_total} / 5.0"
        )

    return f"""## Scoring Results

**Student ID**: {student_id}
{score_header}
**Grade**: {grade}

### Per-Dimension Scores

{dim_text}

---

## Task

Based on the scoring results above, write a student-facing comment with these \
sections:

### [Strengths]
Highlight the 1-2 dimensions where the student performed best. Reference \
specific content from their submission (use the evidence field). Explain WHY \
this is good work, not just THAT it is good.

### [Weaknesses]
Address the 1-2 dimensions with the lowest scores. Describe the specific gap \
between what was submitted and what a higher-scoring submission would contain. \
Be direct but respectful.

### [Suggestions]
Provide 2-3 concrete, prioritized improvement actions. Each should be \
achievable in the student's next assignment. Order by impact (most important \
first).

## Output Format

Return **only** the following JSON (no markdown fences):

{{
  "strengths": "<strengths paragraph>",
  "weaknesses": "<weaknesses paragraph>",
  "suggestions": "<suggestions paragraph>",
  "full_text": "<all three sections combined as a single natural-language comment>"
}}"""


def build_comment_system_prompt(rubric: Rubric) -> str:
    """Build the system prompt for comment generation."""
    cg = rubric.comment_guidelines
    return COMMENT_SYSTEM_PROMPT_TEMPLATE.format(
        language=cg.language,
        min_length=cg.length_range[0] if cg.length_range else 200,
        max_length=cg.length_range[1] if len(cg.length_range) > 1 else 400,
        tone=cg.tone,
        prohibited="; ".join(cg.prohibited_patterns) if cg.prohibited_patterns else "None",
    )


# ---------------------------------------------------------------------------
# Response parsing and validation
# ---------------------------------------------------------------------------


def extract_json_from_response(text: str) -> dict[str, Any]:
    """Parse JSON from the model response, stripping markdown fences if present."""
    cleaned = text.strip()

    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        # Find end of opening fence line
        first_newline = cleaned.index("\n")
        # Find closing fence
        last_fence = cleaned.rfind("```")
        if last_fence > first_newline:
            cleaned = cleaned[first_newline + 1 : last_fence].strip()

    return json.loads(cleaned)


def _coerce_score(raw_score: Any) -> Any:
    if isinstance(raw_score, int):
        return raw_score
    if isinstance(raw_score, float) and raw_score.is_integer():
        return int(raw_score)
    if isinstance(raw_score, str):
        text = raw_score.strip()
        if text.isdigit():
            return int(text)
        try:
            float_value = float(text)
        except ValueError:
            return raw_score
        if float_value.is_integer():
            return int(float_value)
    return raw_score


def _coerce_confidence(raw_confidence: Any) -> Any:
    if isinstance(raw_confidence, (int, float)):
        return float(raw_confidence)
    if isinstance(raw_confidence, str):
        try:
            return float(raw_confidence.strip())
        except ValueError:
            return raw_confidence
    return raw_confidence


def validate_scoring_response(
    data: dict[str, Any],
    rubric: Rubric,
) -> list[str]:
    """Validate a scoring response against the Rubric.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []

    dims = data.get("dimension_scores")
    if not isinstance(dims, list) or len(dims) == 0:
        errors.append("Missing or empty dimension_scores")
        return errors

    rubric_criteria = list(rubric.criteria)
    rubric_by_id = {criterion.criterion_id: criterion for criterion in rubric_criteria}

    if len(dims) != len(rubric_criteria):
        errors.append(
            f"dimension_scores length mismatch: expected {len(rubric_criteria)}, got {len(dims)}"
        )

    seen_dims: dict[str, dict[str, Any]] = {}
    for i, dim in enumerate(dims):
        if not isinstance(dim, dict):
            errors.append(f"dimension_scores[{i}] must be an object")
            continue

        criterion_id = str(dim.get("criterion_id", "")).strip()
        if not criterion_id:
            errors.append(f"dimension_scores[{i}] missing criterion_id")
            continue
        if criterion_id not in rubric_by_id:
            errors.append(f"Unknown criterion_id '{criterion_id}'")
            continue
        if criterion_id in seen_dims:
            errors.append(f"Duplicate criterion_id '{criterion_id}'")
            continue

        rc = rubric_by_id[criterion_id]
        dim["criterion_id"] = rc.criterion_id
        dim["criterion_name"] = rc.name
        dim["weight"] = rc.weight
        dim["max_score"] = _criterion_max_score(rc)
        dim["score"] = _coerce_score(dim.get("score"))
        dim["confidence"] = _coerce_confidence(dim.get("confidence"))

        score = dim.get("score")
        if rubric.score_mode == "raw":
            max_score = _criterion_max_score(rc)
            if not isinstance(score, int) or score < 0 or score > max_score:
                errors.append(
                    f"Criterion '{criterion_id}': score must be integer 0-{max_score} (got {score})"
                )
        elif (
            not isinstance(score, int)
            or score < _criterion_min_score(rc, rubric.score_mode)
            or score not in set(rc.scale)
        ):
            errors.append(
                f"Criterion '{criterion_id}': score must be one of {rc.scale} (got {score})"
            )

        confidence = dim.get("confidence")
        if confidence is not None and (
            not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1
        ):
            errors.append(
                f"Criterion '{criterion_id}': confidence must be 0.0-1.0 (got {confidence})"
            )

        seen_dims[criterion_id] = dim

    missing_criteria = [
        criterion.criterion_id
        for criterion in rubric_criteria
        if criterion.criterion_id not in seen_dims
    ]
    if missing_criteria:
        errors.append(f"Missing criteria in response: {missing_criteria}")

    ordered_dims = [
        seen_dims[criterion.criterion_id]
        for criterion in rubric_criteria
        if criterion.criterion_id in seen_dims
    ]
    data["dimension_scores"] = ordered_dims

    expected_total = 0.0
    for rc in rubric_criteria:
        dim = seen_dims.get(rc.criterion_id)
        if dim is None:
            continue
        score = dim.get("score", 0)
        try:
            if rubric.score_mode == "raw":
                expected_total += float(score)
            else:
                expected_total += rc.weight * float(score)
        except Exception:
            errors.append(f"Invalid score for '{rc.criterion_id}': {score}")

    expected_total = round(expected_total, 2)
    total_key = "raw_total_score" if rubric.score_mode == "raw" else "weighted_total"
    total_value = data.get(total_key)
    try:
        total_value_float = float(total_value)
    except (TypeError, ValueError):
        total_value_float = None
    if total_value_float is None or abs(total_value_float - expected_total) > 0.1:
        errors.append(
            f"{total_key} mismatch: response={total_value}, computed={expected_total}"
        )
        data[total_key] = expected_total

    if rubric.score_mode == "raw":
        max_total_score = float(data.get("max_total_score", rubric.max_total_score) or rubric.max_total_score or 0.0)
        if max_total_score <= 0:
            max_total_score = float(sum(_criterion_max_score(c) for c in rubric.criteria))
        data["max_total_score"] = round(max_total_score, 2)
        expected_normalized = _normalize_total_score(expected_total, max_total_score)
        weighted_total = data.get("weighted_total")
        try:
            weighted_total_float = float(weighted_total)
        except (TypeError, ValueError):
            weighted_total_float = None
        if weighted_total_float is None or abs(weighted_total_float - expected_normalized) > 0.1:
            data["weighted_total"] = expected_normalized
    else:
        data["weighted_total"] = expected_total

    confidence_values = [
        float(dim["confidence"])
        for dim in ordered_dims
        if isinstance(dim.get("confidence"), (int, float))
    ]
    expected_confidence = (
        round(sum(confidence_values) / len(confidence_values), 2)
        if confidence_values
        else 0.0
    )
    overall_confidence = data.get("overall_confidence")
    if overall_confidence is not None:
        overall_confidence = _coerce_confidence(overall_confidence)
        data["overall_confidence"] = overall_confidence
    if (
        overall_confidence is None
        or not isinstance(overall_confidence, (int, float))
        or abs(float(overall_confidence) - expected_confidence) > 0.1
    ):
        errors.append(
            "overall_confidence mismatch: "
            f"response={overall_confidence}, computed={expected_confidence}"
        )
        data["overall_confidence"] = expected_confidence

    return errors


def validate_comment_response(data: dict[str, Any]) -> list[str]:
    """Validate a comment generation response."""
    errors: list[str] = []
    for key in ("strengths", "weaknesses", "suggestions"):
        val = data.get(key)
        if not val or not isinstance(val, str):
            errors.append(f"Missing or empty '{key}' in comment response")
    return errors


def _has_gate_warning(gate_status: dict[str, Any]) -> bool:
    for gate in gate_status.get("details", []):
        if not gate.get("passed", True) and gate.get("on_fail") in {"flag", "warn"}:
            return True
    return False


def _append_text_instruction(
    user_content: list[dict[str, Any]],
    instruction: str,
) -> list[dict[str, Any]]:
    updated = list(user_content)
    updated.append({"type": "text", "text": instruction})
    return updated


def _truncate_for_prompt(text: str, max_chars: int = 1800) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _build_scoring_repair_instruction(
    rubric: Rubric,
    issues: list[str],
    previous_response: str,
) -> str:
    criterion_ids = ", ".join(criterion.criterion_id for criterion in rubric.criteria)
    issue_text = "\n".join(f"- {issue}" for issue in issues)
    return (
        "Your previous scoring response was invalid.\n"
        f"Exact criterion IDs allowed: {criterion_ids}\n"
        "Re-score the submission from scratch and return valid JSON only.\n"
        "Do not omit, rename, or duplicate any criterion_id.\n"
        "Validation issues:\n"
        f"{issue_text}\n"
        "Previous invalid response:\n"
        f"{_truncate_for_prompt(previous_response)}"
    )


async def _score_submission_json(
    model: str,
    rubric: Rubric,
    semaphore: asyncio.Semaphore,
    user_content: list[dict[str, Any]],
    context: str,
) -> dict[str, Any]:
    total_input_tokens = 0
    total_output_tokens = 0
    repaired = False
    attempt_issues: list[str] = []
    current_user_content = list(user_content)

    for attempt in range(1, MAX_SCORING_ATTEMPTS + 1):
        async with semaphore:
            response_data = await asyncio.to_thread(
                _call_with_retry,
                model=model,
                system_prompt=SCORING_SYSTEM_PROMPT,
                user_content=current_user_content,
                context=f"{context} attempt {attempt}",
            )
        total_input_tokens += response_data["_input_tokens"]
        total_output_tokens += response_data["_output_tokens"]

        try:
            score_json = extract_json_from_response(response_data["_text"])
            issues = validate_scoring_response(score_json, rubric)
        except json.JSONDecodeError as exc:
            score_json = None
            issues = [f"json_parse_error: {exc}"]

        if not issues and score_json is not None:
            return {
                "score_json": score_json,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "repaired": repaired,
                "validation_errors": attempt_issues,
            }

        attempt_issues.extend(issues)
        if attempt >= MAX_SCORING_ATTEMPTS:
            raise InvalidScoringResponseError("; ".join(attempt_issues))

        repaired = True
        current_user_content = _append_text_instruction(
            user_content,
            _build_scoring_repair_instruction(rubric, issues, response_data["_text"]),
        )

    raise InvalidScoringResponseError("Scoring response validation exhausted")


def _should_run_second_pass(
    score_json: dict[str, Any],
    rubric: Rubric,
    gate_status: dict[str, Any],
    evidence_quality: str,
    repaired: bool,
) -> list[str]:
    reasons: list[str] = []
    threshold_total = float(
        score_json.get("raw_total_score", 0.0) if rubric.score_mode == "raw"
        else score_json.get("weighted_total", 0.0) or 0.0
    )
    overall_confidence = float(score_json.get("overall_confidence", 0.0) or 0.0)

    if overall_confidence < SECOND_PASS_CONFIDENCE_THRESHOLD:
        reasons.append("low_confidence")
    if _has_gate_warning(gate_status):
        reasons.append("gate_warning")
    if repaired:
        reasons.append("repaired_output")
    if evidence_quality != "complete":
        reasons.append("partial_evidence")
    if abs(threshold_total - rubric.thresholds.accept) <= SECOND_PASS_MARGIN_THRESHOLD:
        reasons.append("near_accept_threshold")
    if abs(threshold_total - rubric.thresholds.reject) <= SECOND_PASS_MARGIN_THRESHOLD:
        reasons.append("near_reject_threshold")
    return reasons


def _merge_scoring_results(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    rubric: Rubric,
) -> tuple[dict[str, Any], bool, dict[str, Any]]:
    primary_dims = {
        dim["criterion_id"]: dim for dim in primary.get("dimension_scores", [])
    }
    secondary_dims = {
        dim["criterion_id"]: dim for dim in secondary.get("dimension_scores", [])
    }

    merged_dims: list[dict[str, Any]] = []
    max_dim_diff = 0
    for criterion in rubric.criteria:
        first = primary_dims[criterion.criterion_id]
        second = secondary_dims[criterion.criterion_id]
        first_score = int(first.get("score", 0))
        second_score = int(second.get("score", 0))
        max_dim_diff = max(max_dim_diff, abs(first_score - second_score))

        exemplar = first
        if float(second.get("confidence", 0.0) or 0.0) > float(first.get("confidence", 0.0) or 0.0):
            exemplar = second

        avg_score = int(round((first_score + second_score) / 2))
        avg_score = max(_criterion_min_score(criterion, rubric.score_mode), min(_criterion_max_score(criterion), avg_score))
        avg_confidence = round(
            (
                float(first.get("confidence", 0.0) or 0.0)
                + float(second.get("confidence", 0.0) or 0.0)
            ) / 2,
            2,
        )

        merged_dims.append(
            {
                "criterion_id": criterion.criterion_id,
                "criterion_name": criterion.name,
                "weight": criterion.weight,
                "max_score": _criterion_max_score(criterion),
                "score": avg_score,
                "evidence": exemplar.get("evidence", ""),
                "reasoning": exemplar.get("reasoning", ""),
                "matched_core_points": exemplar.get("matched_core_points", []),
                "accepted_alternative_reasoning": exemplar.get("accepted_alternative_reasoning", ""),
                "missing_points": exemplar.get("missing_points", []),
                "logic_issues": exemplar.get("logic_issues", []),
                "improvement": exemplar.get("improvement", ""),
                "confidence": avg_confidence,
            }
        )

    if rubric.score_mode == "raw":
        merged_total = round(sum(dim["score"] for dim in merged_dims), 2)
        max_total_score = round(float(rubric.max_total_score or sum(_criterion_max_score(c) for c in rubric.criteria)), 2)
        normalized_total = _normalize_total_score(merged_total, max_total_score)
    else:
        merged_total = round(
            sum(dim["weight"] * dim["score"] for dim in merged_dims),
            2,
        )
        max_total_score = 0.0
        normalized_total = merged_total
    merged_confidence = round(
        sum(float(dim["confidence"]) for dim in merged_dims) / len(merged_dims),
        2,
    )
    if rubric.score_mode == "raw":
        total_diff = abs(
            float(primary.get("raw_total_score", 0.0) or 0.0)
            - float(secondary.get("raw_total_score", 0.0) or 0.0)
        )
    else:
        total_diff = abs(
            float(primary.get("weighted_total", 0.0) or 0.0)
            - float(secondary.get("weighted_total", 0.0) or 0.0)
        )
    disagreement = (
        total_diff > SECOND_PASS_TOTAL_DIFF_THRESHOLD
        or max_dim_diff > SECOND_PASS_DIM_DIFF_THRESHOLD
    )
    merged = {
        "student_id": primary.get("student_id", secondary.get("student_id", "")),
        "rubric_id": primary.get("rubric_id", secondary.get("rubric_id", "")),
        "dimension_scores": merged_dims,
        "weighted_total": normalized_total,
        "overall_confidence": merged_confidence,
    }
    if rubric.score_mode == "raw":
        merged["raw_total_score"] = merged_total
        merged["max_total_score"] = max_total_score
    details = {
        ("raw_total_score_diff" if rubric.score_mode == "raw" else "weighted_total_diff"): round(total_diff, 2),
        "max_dimension_diff": max_dim_diff,
    }
    return merged, disagreement, details


# ---------------------------------------------------------------------------
# IR file loading
# ---------------------------------------------------------------------------


def load_ir_file(path: Path) -> dict[str, Any]:
    """Load and return an IR JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_submission_content(ir: dict[str, Any]) -> str:
    """Extract submission content from an IR record for the scoring prompt."""
    content = ir.get("content", {})
    submission_type = ir.get("submission_type", "text")
    evidence_quality = content.get("evidence_quality", "complete")

    blocks: list[str] = [
        "## Submission Evidence Summary",
        f"- Submission type: {submission_type}",
        f"- Evidence quality: {evidence_quality}",
    ]

    text_sections: list[str] = []
    subjective_payload = content.get("subjective_answers", {})
    subjective_map = (
        subjective_payload.get("answers", {})
        if isinstance(subjective_payload, dict)
        else {}
    )

    assignment_text = content.get("assignment_text", "")
    student_answer = content.get("student_answer", "")
    full_text = student_answer or content.get("full_text", "")
    if assignment_text:
        blocks.append(
            "- Assignment prompt detected and removed from the main scoring text."
        )
    if evidence_quality != "complete":
        blocks.append(
            "- Evidence may be partial. Score conservatively and lower confidence where appropriate."
        )

    subjective_sections: list[str] = []
    if isinstance(subjective_map, dict) and subjective_map:
        blocks.append(
            "- Targeted subjective-question transcriptions are available. Use them as the primary evidence for short-answer and comprehensive questions."
        )
        for key, entry in subjective_map.items():
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("criterion_name", "")).strip() or str(entry.get("criterion_id", key)).strip() or str(key)
            question_type = str(entry.get("question_type", "")).strip()
            transcribed_answer = str(entry.get("transcribed_answer", "")).strip()
            if not transcribed_answer:
                continue
            confidence = entry.get("confidence", 0.0)
            needs_review = bool(entry.get("needs_review", False))
            subjective_sections.append(
                "\n".join(
                    [
                        f"### {title}",
                        f"Question type: {question_type or 'unknown'}",
                        f"Transcription confidence: {confidence}",
                        f"Needs review: {needs_review}",
                        "Student answer:",
                        transcribed_answer,
                    ]
                )
            )

    if subjective_sections:
        text_sections.append("## Targeted Subjective Answers\n\n" + "\n\n".join(subjective_sections))
    elif full_text:
        text_sections.append("## Full Text\n\n" + full_text.strip())

    sections = content.get("sections", [])
    if sections and not full_text and not subjective_sections:
        parts = []
        for section in sections:
            heading = section.get("heading", "")
            level = section.get("level", 2)
            text_value = section.get("text", "")
            prefix = "#" * level
            parts.append(f"{prefix} {heading}\n\n{text_value}")
        if parts:
            text_sections.append("## Sections\n\n" + "\n\n".join(parts))

    transcript = content.get("transcript", "")
    if transcript and not full_text:
        text_sections.append("## Transcript\n\n" + transcript.strip())

    images = content.get("images", [])
    image_sections: list[str] = []
    for i, img in enumerate(images, 1):
        item_lines = [f"### Image {i}"]
        for key, label in (
            ("type", "Heuristic Type (may be wrong)"),
            ("caption", "Caption"),
            ("description", "Description"),
            ("extracted_text", "Extracted Text"),
            ("ocr_text", "OCR Text"),
            ("alt_text", "Alt Text"),
            ("context", "Context"),
        ):
            value = img.get(key, "")
            if value:
                item_lines.append(f"{label}: {value}")

        remaining_pairs = []
        for key, value in img.items():
            if key in {
                "type",
                "caption",
                "description",
                "extracted_text",
                "ocr_text",
                "alt_text",
                "context",
            }:
                continue
            if isinstance(value, (str, int, float, bool)) and str(value).strip():
                remaining_pairs.append(f"{key}={value}")

        if remaining_pairs:
            item_lines.append("Metadata: " + "; ".join(remaining_pairs))

        image_sections.append("\n".join(item_lines))

    blocks.append(f"- Image/diagram count: {len(images)}")

    if text_sections:
        blocks.extend(text_sections)
    if image_sections:
        blocks.append(
            "## Images / Diagrams\n\n"
            "Note: image type/description fields are heuristic. "
            "Always judge the diagram from the image itself.\n\n"
            + "\n\n".join(image_sections)
        )
    if len(blocks) == 2:
        blocks.append("(No content extracted)")

    return "\n\n".join(blocks)



def _resolve_workspace_source_file(workspace: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/")
    return workspace / Path(*[part for part in normalized.split("/") if part])


def _maybe_upscale_image(image_bytes: bytes) -> bytes:
    """Best-effort upscale to improve diagram readability for vision models."""
    if Image is None:
        return image_bytes
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            max_dim = max(width, height)
            if max_dim >= 2400:
                return image_bytes

            scale = 2 if max_dim >= 1200 else 3
            new_size = (int(width * scale), int(height * scale))
            resampling = getattr(Image, "Resampling", Image)
            resized = img.resize(new_size, resample=getattr(resampling, "LANCZOS"))
            out = io.BytesIO()
            resized.save(out, format="PNG")
            data = out.getvalue()
            if len(data) <= MAX_IMAGE_BYTES:
                return data
    except Exception as exc:
        logger.warning("Image upscale failed: %s", exc)
    return image_bytes


def _guess_media_type(path_str: str) -> str | None:
    suffix = Path(path_str).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return None


def _image_priority(image_entry: dict[str, Any]) -> tuple[int, int]:
    image_type = str(image_entry.get("type", "")).lower()
    ocr_status = str(image_entry.get("ocr_status", "")).lower()
    priority = 9
    if "sequence" in image_type:
        priority = 0
    elif "diagram" in image_type:
        priority = 1
    elif "flow" in image_type:
        priority = 2
    elif image_type and image_type != "image":
        priority = 3
    elif image_entry.get("caption") or image_entry.get("context"):
        priority = 4
    return (priority, 0 if ocr_status == "success" else 1)


def _load_image_bytes_for_entry(
    workspace: Path,
    ir: dict[str, Any],
    image_entry: dict[str, Any],
) -> tuple[bytes, str] | None:
    file_ref = str(image_entry.get("file", ""))
    container_path = str(image_entry.get("container_path", ""))

    if file_ref.startswith("raw/"):
        source_path = _resolve_workspace_source_file(workspace, file_ref)
        if source_path.is_file():
            return source_path.read_bytes(), source_path.name

    if container_path:
        for source in ir.get("source_files", []):
            source_str = str(source)
            if not source_str.lower().endswith(".docx"):
                continue
            docx_path = _resolve_workspace_source_file(workspace, source_str)
            if not docx_path.is_file():
                continue
            with zipfile.ZipFile(docx_path) as zf:
                if container_path in zf.namelist():
                    return zf.read(container_path), container_path

    return None


def build_scoring_message_content(
    workspace: Path,
    rubric: Rubric,
    ir: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    student_id = ir.get("student_id", "unknown")
    submission_type = ir.get("submission_type", "text")
    content_text = get_submission_content(ir)
    prompt = build_scoring_user_prompt(rubric, student_id, content_text, submission_type)

    user_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    image_entries = list(ir.get("content", {}).get("images", []))
    attached_count = 0

    if image_entries:
        user_content.append(
            {
                "type": "text",
                "text": (
                    "The submission has image evidence. Inspect every attached image directly, "
                    "especially for diagram-related criteria. Do not rely only on OCR summaries."
                ),
            }
        )

    for image_entry in sorted(image_entries, key=_image_priority):
        if attached_count >= MAX_ATTACHED_IMAGES:
            break
        loaded = _load_image_bytes_for_entry(workspace, ir, image_entry)
        if loaded is None:
            continue
        image_bytes, image_name = loaded
        image_bytes = _maybe_upscale_image(image_bytes)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            logger.warning(
                "Skipping oversized image for %s: %s (%d bytes)",
                student_id,
                image_name,
                len(image_bytes),
            )
            continue

        media_type = _guess_media_type(image_name)
        if media_type is None:
            logger.warning("Skipping unsupported image type for %s: %s", student_id, image_name)
            continue

        caption = str(image_entry.get("caption", "")).strip()
        if not caption:
            caption = image_name
        user_content.append(
            {
                "type": "text",
                "text": f"Attached image {attached_count + 1}: {caption}",
            }
        )
        user_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                },
            }
        )
        attached_count += 1

    return user_content, attached_count


def _is_objective_criterion(criterion: RubricCriterion) -> bool:
    return criterion.question_type in OBJECTIVE_QUESTION_TYPES


def _objective_answer_map(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = ir.get("content", {}).get("objective_answers", {})
    answers = payload.get("answers", {}) if isinstance(payload, dict) else {}
    return answers if isinstance(answers, dict) else {}


def _subjective_answer_map(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = ir.get("content", {}).get("subjective_answers", {})
    answers = payload.get("answers", {}) if isinstance(payload, dict) else {}
    return answers if isinstance(answers, dict) else {}


def _subjective_entry_for_criterion(
    ir: dict[str, Any],
    criterion: RubricCriterion,
) -> dict[str, Any] | None:
    answer_map = _subjective_answer_map(ir)
    direct = answer_map.get(criterion.criterion_id)
    if isinstance(direct, dict):
        return direct

    question_id = _extract_question_id(criterion)
    if criterion.question_type == "short_answer" and question_id.isdigit():
        by_qid = answer_map.get(f"q{question_id}")
        if isinstance(by_qid, dict):
            return by_qid
    return None


def _subjective_review_reasons(ir: dict[str, Any], rubric: Rubric) -> list[str]:
    reasons: list[str] = []
    for criterion in rubric.criteria:
        if _is_objective_criterion(criterion):
            continue
        entry = _subjective_entry_for_criterion(ir, criterion)
        if entry is None:
            continue
        if bool(entry.get("needs_review", False)):
            reasons.append(criterion.criterion_id)
    return reasons


def _extract_question_id(criterion: RubricCriterion) -> str:
    if isinstance(criterion.answer_key, dict):
        return str(criterion.answer_key.get("question_id", "")).strip()
    return ""


def _extract_fill_blank_line(text: str, question_id: str) -> str:
    pattern = re.compile(rf"(?m)^\s*{re.escape(question_id)}[、,，.．]\s*(.+)$")
    matches = pattern.findall(text)
    if not matches:
        return ""
    return matches[-1].strip()


def _extract_fill_blank_answer(ir: dict[str, Any], criterion: RubricCriterion) -> str:
    question_id = _extract_question_id(criterion)
    blank_id = ""
    if isinstance(criterion.answer_key, dict):
        blank_id = str(criterion.answer_key.get("blank_id", "")).strip()
    if not question_id or not blank_id.isdigit():
        return ""

    text = str(ir.get("content", {}).get("student_answer", "") or ir.get("content", {}).get("full_text", ""))
    line = _extract_fill_blank_line(text, question_id)
    if not line:
        return ""

    normalized = re.sub(r"[_\s]+", " ", line).strip()
    parts = [
        part.strip()
        for part in re.split(r"[，,、；;]", normalized)
        if part.strip()
    ]
    blank_index = int(blank_id) - 1
    if blank_index < 0 or blank_index >= len(parts):
        return ""
    return parts[blank_index]


def _objective_improvement(criterion: RubricCriterion, score: int) -> str:
    if score >= _criterion_max_score(criterion):
        return "Keep this objective item accurate and maintain the same level of care."
    if criterion.question_type == "fill_blank":
        return "Recheck the exact fixed-answer term and keep the wording consistent with the required answer key."
    if criterion.question_type == "judgment":
        return "Recheck the statement against the fixed judgment key before selecting the mark."
    return "Recheck the fixed answer key and verify every selected option before submitting."


def _build_objective_dimension(
    criterion: RubricCriterion,
    score: int,
    evidence: str,
    reasoning: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "criterion_id": criterion.criterion_id,
        "criterion_name": criterion.name,
        "weight": criterion.weight,
        "max_score": _criterion_max_score(criterion),
        "score": score,
        "evidence": evidence,
        "reasoning": reasoning,
        "matched_core_points": [],
        "accepted_alternative_reasoning": "",
        "missing_points": [],
        "logic_issues": [],
        "improvement": _objective_improvement(criterion, score),
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
    }


def _score_single_choice(
    criterion: RubricCriterion,
    answer_entry: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    expected = str((criterion.answer_key or {}).get("correct_option", "")).strip().upper()
    recognized = ""
    confidence = 0.0
    needs_review = True
    if answer_entry:
        recognized = str(answer_entry.get("recognized_answer", "")).strip().upper()
        confidence = float(answer_entry.get("confidence", 0.0) or 0.0)
        needs_review = bool(answer_entry.get("needs_review", False))
    score = criterion.max_score if recognized == expected and expected else 0
    evidence = (
        f"Recognized answer: {recognized or 'unknown'}; expected: {expected or 'unknown'}; "
        f"vision_confidence={confidence:.2f}."
    )
    reasoning = (
        "The recognized option matches the fixed answer key."
        if score == criterion.max_score
        else "The recognized option does not match the fixed answer key or could not be read reliably."
    )
    return _build_objective_dimension(criterion, score, evidence, reasoning, confidence), needs_review or not recognized


def _score_multiple_choice(
    criterion: RubricCriterion,
    answer_entry: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    correct = sorted(str(item).strip().upper() for item in (criterion.answer_key or {}).get("correct_options", []) if str(item).strip())
    recognized: list[str] = []
    confidence = 0.0
    needs_review = True
    if answer_entry:
        raw_answer = answer_entry.get("recognized_answer", [])
        if isinstance(raw_answer, list):
            recognized = sorted(str(item).strip().upper() for item in raw_answer if str(item).strip())
        confidence = float(answer_entry.get("confidence", 0.0) or 0.0)
        needs_review = bool(answer_entry.get("needs_review", False))

    recognized_set = set(recognized)
    correct_set = set(correct)
    wrong_selection = bool(recognized_set - correct_set)
    correct_hit_count = len(recognized_set & correct_set)

    if not recognized or recognized == ["UNKNOWN"] or wrong_selection:
        score = 0
    elif correct_hit_count == len(correct_set) and recognized_set == correct_set:
        score = criterion.max_score
    elif correct_hit_count == 1:
        score = 1
    elif correct_hit_count >= 2:
        score = 3
    else:
        score = 0

    evidence = (
        f"Recognized answers: {recognized or ['unknown']}; expected: {correct}; "
        f"vision_confidence={confidence:.2f}."
    )
    if wrong_selection:
        reasoning = "At least one wrong option was selected, so the item scores 0 under the fixed-answer rule."
    elif score == criterion.max_score:
        reasoning = "All correct options were selected and no wrong options were selected."
    elif score == 3:
        reasoning = "Two or more correct options were selected without wrong selections, but the answer is not fully complete."
    elif score == 1:
        reasoning = "Exactly one correct option was selected and there were no wrong selections."
    else:
        reasoning = "The recognized answers are missing or insufficient to earn credit under the fixed-answer rule."

    return _build_objective_dimension(criterion, score, evidence, reasoning, confidence), needs_review or not recognized


def _score_judgment(
    criterion: RubricCriterion,
    answer_entry: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    expected = str((criterion.answer_key or {}).get("correct_value", "")).strip()
    recognized = ""
    confidence = 0.0
    needs_review = True
    if answer_entry:
        recognized = str(answer_entry.get("recognized_answer", "")).strip()
        confidence = float(answer_entry.get("confidence", 0.0) or 0.0)
        needs_review = bool(answer_entry.get("needs_review", False))
    score = criterion.max_score if recognized == expected and expected in {"√", "×"} else 0
    evidence = (
        f"Recognized judgment mark: {recognized or 'unknown'}; expected: {expected or 'unknown'}; "
        f"vision_confidence={confidence:.2f}."
    )
    reasoning = (
        "The recognized judgment mark matches the fixed answer key."
        if score == criterion.max_score
        else "The recognized judgment mark does not match the fixed answer key or could not be read reliably."
    )
    return _build_objective_dimension(criterion, score, evidence, reasoning, confidence), needs_review or recognized not in {"√", "×"}


def _score_fill_blank(
    criterion: RubricCriterion,
    ir: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    recognized = _extract_fill_blank_answer(ir, criterion)
    expected = str((criterion.answer_key or {}).get("literal_answer", "")).strip()
    score = criterion.max_score if recognized == expected and expected else 0
    confidence = 0.98 if recognized else 0.0
    evidence = f"Extracted fill-blank answer: {recognized or 'unknown'}; expected: {expected or 'unknown'}."
    reasoning = (
        "The extracted fill-blank answer matches the fixed answer key exactly."
        if score == criterion.max_score
        else "The extracted fill-blank answer does not match the fixed answer key exactly or could not be found."
    )
    return _build_objective_dimension(criterion, score, evidence, reasoning, confidence), not recognized


def score_objective_criteria(
    ir: dict[str, Any],
    rubric: Rubric,
) -> tuple[list[dict[str, Any]], list[str]]:
    answers = _objective_answer_map(ir)
    dimensions: list[dict[str, Any]] = []
    review_reasons: list[str] = []

    for criterion in rubric.criteria:
        if not _is_objective_criterion(criterion):
            continue
        question_id = _extract_question_id(criterion)
        answer_entry = answers.get(question_id)

        if criterion.question_type == "single_choice":
            dim, needs_review = _score_single_choice(criterion, answer_entry)
        elif criterion.question_type == "multiple_choice":
            dim, needs_review = _score_multiple_choice(criterion, answer_entry)
        elif criterion.question_type == "judgment":
            dim, needs_review = _score_judgment(criterion, answer_entry)
        else:
            dim, needs_review = _score_fill_blank(criterion, ir)

        dimensions.append(dim)
        if needs_review:
            review_reasons.append(criterion.criterion_id)

    return dimensions, review_reasons


def merge_dimension_scores(
    rubric: Rubric,
    objective_dimensions: list[dict[str, Any]],
    subjective_dimensions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {dim["criterion_id"]: dim for dim in objective_dimensions + subjective_dimensions}
    return [by_id[criterion.criterion_id] for criterion in rubric.criteria if criterion.criterion_id in by_id]

# ---------------------------------------------------------------------------
# Score file writing (atomic)
# ---------------------------------------------------------------------------


def save_score_file(scores_dir: Path, student_id: str, data: dict[str, Any]) -> None:
    """Atomically write a score JSON file.

    Writes to a temporary file first, then renames to ensure data
    integrity if the process is interrupted.
    """
    scores_dir.mkdir(parents=True, exist_ok=True)
    target = scores_dir / f"{student_id}.json"

    # Write to temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(scores_dir), suffix=".tmp", prefix=f"{student_id}_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Atomic rename (same filesystem)
        os.replace(tmp_path, str(target))
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    logger.debug("Saved score: %s", target)


# ---------------------------------------------------------------------------
# Progress file management
# ---------------------------------------------------------------------------


def load_progress(path: Path) -> Progress | None:
    """Load progress.json if it exists."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Reconstruct FailedItem objects
    failed_items = []
    for fi in raw.get("failed_ids", []):
        if isinstance(fi, dict):
            failed_items.append(
                FailedItem(
                    id=fi.get("id", ""),
                    error=fi.get("error", ""),
                    attempts=fi.get("attempts", 0),
                    last_attempt=fi.get("last_attempt", ""),
                )
            )

    return Progress(
        batch_id=raw.get("batch_id", ""),
        rubric_id=raw.get("rubric_id", ""),
        mode=raw.get("mode", "real-time"),
        started_at=raw.get("started_at", ""),
        last_updated=raw.get("last_updated", ""),
        total=raw.get("total", 0),
        completed=raw.get("completed", 0),
        failed=raw.get("failed", 0),
        pending=raw.get("pending", 0),
        completed_ids=raw.get("completed_ids", []),
        failed_ids=failed_items,
        pending_ids=raw.get("pending_ids", []),
        processing_order=raw.get("processing_order", []),
        stats=raw.get("stats", {}),
    )


def save_progress(path: Path, progress: Progress) -> None:
    """Save progress.json atomically."""
    progress.last_updated = _now_iso()
    data = asdict(progress)
    # Convert FailedItem dataclasses to dicts (asdict handles this)

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix="progress_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def classify_grade(weighted_total: float, thresholds: RubricThresholds) -> str:
    """Classify a weighted total into accept/review/reject."""
    if weighted_total >= thresholds.accept:
        return "accept"
    if weighted_total < thresholds.reject:
        return "reject"
    return "review"


def compute_percentile(weighted_total: float) -> int:
    """Map 1-5 weighted total to 40-100 percentile scale."""
    return round((weighted_total - 1) / 4 * 60 + 40)


def compute_percentile_from_raw(raw_total_score: float, max_total_score: float) -> int:
    """Map a raw exam score to a 0-100 percentage-like percentile."""
    if max_total_score <= 0:
        return 0
    ratio = max(0.0, min(1.0, raw_total_score / max_total_score))
    return round(ratio * 100)


def determine_review_flag(
    overall_confidence: float,
    gate_status: dict[str, Any],
    evidence_quality: str = "complete",
    forced_flag: str = "",
) -> str:
    """Determine the review flag for a scored submission."""
    if forced_flag:
        return forced_flag
    if evidence_quality != "complete":
        return "low_confidence"
    if overall_confidence < 0.6:
        return "low_confidence"
    if _has_gate_warning(gate_status):
        return "gate_warning"
    return "none"


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    batch_mode: bool,
) -> float:
    """Estimate USD cost for a set of tokens."""
    discount = 0.5 if batch_mode else 1.0
    cost = (
        input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
        + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
    ) * discount
    return round(cost, 6)


def _set_runtime_config_path(path: Path | None) -> None:
    """Override the runtime config file for this process."""
    global _CONFIG_PATH_OVERRIDE, _PROJECT_CONFIG
    if path is None:
        _CONFIG_PATH_OVERRIDE = None
    else:
        _CONFIG_PATH_OVERRIDE = path if path.is_absolute() else PROJECT_ROOT / path
    _PROJECT_CONFIG = None


def _runtime_config_path() -> Path:
    """Resolve the runtime config path from CLI/env/default precedence."""
    if _CONFIG_PATH_OVERRIDE is not None:
        return _CONFIG_PATH_OVERRIDE

    configured = os.environ.get("GRADER_CONFIG_PATH", "").strip()
    if not configured:
        return DEFAULT_CONFIG_PATH

    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _load_project_config() -> dict[str, Any]:
    """Load runtime configuration from the resolved config path if present."""
    global _PROJECT_CONFIG
    if _PROJECT_CONFIG is not None:
        return _PROJECT_CONFIG

    config_path = _runtime_config_path()

    if not config_path.exists():
        _PROJECT_CONFIG = {}
        return _PROJECT_CONFIG

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            logger.warning(
                "Ignoring invalid config file %s: top-level value must be a mapping",
                config_path,
            )
            _PROJECT_CONFIG = {}
            return _PROJECT_CONFIG
        _PROJECT_CONFIG = data
        logger.info("Loaded runtime config from %s", config_path)
        return _PROJECT_CONFIG
    except Exception as exc:
        logger.warning("Failed to load config file %s: %s", config_path, exc)
        _PROJECT_CONFIG = {}
        return _PROJECT_CONFIG


def _config_value(*keys: str) -> str:
    """Read a string value from the resolved runtime config file."""
    current: Any = _load_project_config()
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    if current is None:
        return ""
    return str(current).strip()


def _resolve_configured_path(config_value: str) -> Path | None:
    """Resolve a config path relative to the project root."""
    value = config_value.strip()
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _get_openai_client() -> OpenAI:
    """Return a cached OpenAI client configured from environment variables."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        api_key = (
            os.environ.get("OPENAI_API_KEY", "").strip()
            or _config_value("openai", "api_key")
        )
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Configure it in the environment "
                "or grader-config.yaml"
            )
        base_url = (
            os.environ.get("OPENAI_BASE_URL", "").strip()
            or _config_value("openai", "base_url")
        )
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        timeout_value = (
            os.environ.get("OPENAI_TIMEOUT_SECONDS", "").strip()
            or _config_value("openai", "timeout_seconds")
        )
        if timeout_value:
            client_kwargs["timeout"] = float(timeout_value)
        else:
            client_kwargs["timeout"] = 90.0
        client_kwargs["max_retries"] = 0
        _OPENAI_CLIENT = OpenAI(**client_kwargs)
    return _OPENAI_CLIENT


def _build_openai_input(
    system_prompt: str,
    user_content: str | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert the local content representation into Responses API input."""
    if isinstance(user_content, str):
        normalized_user_content = [{"type": "input_text", "text": user_content}]
    else:
        normalized_user_content = []
        for item in user_content:
            if item.get("type") == "text":
                normalized_user_content.append(
                    {"type": "input_text", "text": item.get("text", "")}
                )
                continue

            if item.get("type") == "image":
                source = item.get("source", {})
                if source.get("type") != "base64":
                    continue
                media_type = source.get("media_type", "")
                data = source.get("data", "")
                normalized_user_content.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{media_type};base64,{data}",
                    }
                )

    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": normalized_user_content,
        },
    ]


def _extract_response_text(response: Any) -> str:
    """Extract plain text from a Responses API result."""
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text_value = getattr(content, "text", "")
            if text_value:
                chunks.append(text_value)
    return "\n".join(chunks).strip()


def _serialize_response_for_log(response: Any) -> str:
    """Best-effort JSON serialization for OpenAI SDK response objects."""
    payload: Any

    if hasattr(response, "model_dump"):
        try:
            payload = response.model_dump(mode="json")
        except TypeError:
            payload = response.model_dump()
    elif hasattr(response, "to_dict"):
        payload = response.to_dict()
    elif isinstance(response, dict):
        payload = response
    else:
        payload = {"repr": repr(response)}

    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return json.dumps({"repr": repr(payload)}, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Real-time scoring engine
# ---------------------------------------------------------------------------


async def score_one_submission(
    model: str,
    rubric: Rubric,
    workspace: Path,
    ir: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> ScoringResult:
    """Score a single submission: scoring call + comment call.

    Uses the semaphore for concurrency control. Retries with exponential
    backoff on transient failures.
    """
    student_id = ir.get("student_id", "unknown")

    total_input_tokens = 0
    total_output_tokens = 0
    start_ms = time.monotonic_ns() // 1_000_000

    objective_dimensions, objective_review_reasons = score_objective_criteria(ir, rubric)
    subjective_review_reasons = _subjective_review_reasons(ir, rubric)
    subjective_criteria = [criterion for criterion in rubric.criteria if not _is_objective_criterion(criterion)]
    subjective_rubric = replace(
        rubric,
        criteria=subjective_criteria,
        max_total_score=float(sum(_criterion_max_score(c) for c in subjective_criteria)),
    )

    attached_image_count = 0
    evidence_quality = ir.get("content", {}).get("evidence_quality", "complete")
    gate_status = {
        "all_passed": all(
            g.get("passed", True) for g in ir.get("gate_results", [])
        ),
        "details": ir.get("gate_results", []),
    }

    validation_errors: list[str] = []
    forced_review_flag = "objective_needs_review" if objective_review_reasons else ""
    if subjective_review_reasons:
        forced_review_flag = forced_review_flag or "subjective_transcription_review"
    second_pass_details: dict[str, Any] = {"triggered": False, "reasons": []}
    score_json: dict[str, Any]
    primary_repaired = False

    if subjective_criteria:
        scoring_user_content, attached_image_count = build_scoring_message_content(
            workspace=workspace,
            rubric=subjective_rubric,
            ir=ir,
        )

        primary_scoring = await _score_submission_json(
            model=model,
            rubric=subjective_rubric,
            semaphore=semaphore,
            user_content=scoring_user_content,
            context=f"scoring {student_id}",
        )
        total_input_tokens += primary_scoring["input_tokens"]
        total_output_tokens += primary_scoring["output_tokens"]

        score_json = primary_scoring["score_json"]
        validation_errors = list(primary_scoring["validation_errors"])
        primary_repaired = bool(primary_scoring["repaired"])
        if validation_errors:
            logger.warning(
                "Validation issues repaired for %s: %s",
                student_id,
                "; ".join(validation_errors),
            )

        second_pass_reasons = _should_run_second_pass(
            score_json=score_json,
            rubric=subjective_rubric,
            gate_status=gate_status,
            evidence_quality=evidence_quality,
            repaired=bool(primary_scoring["repaired"]),
        )
        if second_pass_reasons:
            second_pass_content = _append_text_instruction(
                scoring_user_content,
                (
                    "Perform an independent second-pass audit. Score the submission fresh, "
                    "without assuming any prior score is correct. Return JSON only."
                ),
            )
            try:
                second_scoring = await _score_submission_json(
                    model=model,
                    rubric=subjective_rubric,
                    semaphore=semaphore,
                    user_content=second_pass_content,
                    context=f"scoring second pass {student_id}",
                )
                total_input_tokens += second_scoring["input_tokens"]
                total_output_tokens += second_scoring["output_tokens"]
                validation_errors.extend(second_scoring["validation_errors"])

                merged_score_json, disagreement, diff_details = _merge_scoring_results(
                    score_json,
                    second_scoring["score_json"],
                    subjective_rubric,
                )
                score_json = merged_score_json
                second_pass_details = {
                    "triggered": True,
                    "reasons": second_pass_reasons,
                    "diff": diff_details,
                }
                if disagreement:
                    forced_review_flag = forced_review_flag or "score_disagreement"
            except InvalidScoringResponseError as exc:
                validation_errors.append(f"second_pass_invalid: {exc}")
                second_pass_details = {
                    "triggered": True,
                    "reasons": second_pass_reasons,
                    "error": str(exc),
                }
                forced_review_flag = forced_review_flag or "invalid_output"
    else:
        score_json = {
            "student_id": student_id,
            "rubric_id": rubric.id,
            "dimension_scores": [],
            "raw_total_score": 0.0,
            "weighted_total": 1.0,
            "overall_confidence": 0.0,
            "max_total_score": 0.0,
        }

    subjective_dimensions = list(score_json.get("dimension_scores", []))
    merged_dimensions = merge_dimension_scores(rubric, objective_dimensions, subjective_dimensions)
    raw_total_score = round(sum(float(dim.get("score", 0) or 0) for dim in merged_dimensions), 2)
    max_total_score = round(float(rubric.max_total_score or sum(_criterion_max_score(c) for c in rubric.criteria)), 2)
    weighted_total = _normalize_total_score(raw_total_score, max_total_score)
    confidence_values = [
        float(dim.get("confidence", 0.0) or 0.0)
        for dim in merged_dimensions
        if isinstance(dim.get("confidence", 0.0), (int, float))
    ]
    overall_confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0
    score_json = {
        "student_id": student_id,
        "rubric_id": rubric.id,
        "dimension_scores": merged_dimensions,
        "raw_total_score": raw_total_score,
        "max_total_score": max_total_score,
        "weighted_total": weighted_total,
        "overall_confidence": overall_confidence,
    }

    # --- Step 2: Comment generation call ---
    comment_system = build_comment_system_prompt(rubric)
    comment_user = build_comment_user_prompt(rubric, score_json)

    async with semaphore:
        comment_data = await asyncio.to_thread(
            _call_with_retry,
            model=model,
            system_prompt=comment_system,
            user_content=comment_user,
            context=f"comment {student_id}",
        )
    total_input_tokens += comment_data["_input_tokens"]
    total_output_tokens += comment_data["_output_tokens"]

    comment_json = extract_json_from_response(comment_data["_text"])
    comment_errors = validate_comment_response(comment_json)
    if comment_errors:
        logger.warning(
            "Comment validation issues for %s: %s",
            student_id,
            "; ".join(comment_errors),
        )

    # --- Step 3: Assemble final score record ---
    weighted_total = score_json.get("weighted_total", 0.0)
    raw_total_score = score_json.get("raw_total_score")
    max_total_score = score_json.get("max_total_score", rubric.max_total_score)
    overall_confidence = score_json.get("overall_confidence", 0.0)

    duration_ms = time.monotonic_ns() // 1_000_000 - start_ms

    percentile_score = (
        compute_percentile_from_raw(float(raw_total_score or 0.0), float(max_total_score or 0.0))
        if rubric.score_mode == "raw"
        else compute_percentile(weighted_total)
    )
    grade_value = (
        classify_grade(float(raw_total_score or 0.0), rubric.thresholds)
        if rubric.score_mode == "raw"
        else classify_grade(weighted_total, rubric.thresholds)
    )

    final_record = {
        "student_id": student_id,
        "rubric_id": rubric.id,
        "scored_at": _now_iso(),
        "gate_status": gate_status,
        "dimension_scores": score_json.get("dimension_scores", []),
        "weighted_total": weighted_total,
        "percentile_score": percentile_score,
        "grade": grade_value,
        "overall_confidence": overall_confidence,
        "review_flag": determine_review_flag(
            overall_confidence,
            gate_status,
            evidence_quality=evidence_quality,
            forced_flag=forced_review_flag,
        ),
        "comment": {
            "strengths": comment_json.get("strengths", ""),
            "weaknesses": comment_json.get("weaknesses", ""),
            "suggestions": comment_json.get("suggestions", ""),
            "full_text": comment_json.get("full_text", ""),
        },
        "metadata": {
            "score_mode": rubric.score_mode,
            "model": model,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "duration_ms": duration_ms,
            "attached_image_blocks": attached_image_count,
            "validation_errors": list(dict.fromkeys(validation_errors)),
            "evidence_quality": evidence_quality,
            "repaired_response": primary_repaired,
            "second_pass": second_pass_details,
            "objective_review_reasons": objective_review_reasons,
            "objective_answers_status": ir.get("content", {}).get("objective_answers", {}).get("status", "skipped"),
            "subjective_review_reasons": subjective_review_reasons,
            "subjective_answers_status": ir.get("content", {}).get("subjective_answers", {}).get("status", "skipped"),
        },
    }
    if rubric.score_mode == "raw":
        final_record["raw_total_score"] = raw_total_score
        final_record["max_total_score"] = max_total_score

    return ScoringResult(
        student_id=student_id,
        score_data=final_record,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        duration_ms=duration_ms,
    )


def _call_with_retry(
    model: str,
    system_prompt: str,
    user_content: str | list[dict[str, Any]],
    context: str,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """Call the OpenAI Responses API with retry and exponential backoff.

    Returns a dict with _text, _input_tokens, _output_tokens keys.
    """
    backoff = INITIAL_BACKOFF_S
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            client = _get_openai_client()
            response = client.responses.create(
                model=model,
                input=_build_openai_input(system_prompt, user_content),
                max_output_tokens=DEFAULT_MAX_TOKENS,
            )
            usage = getattr(response, "usage", None)
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            text_content = _extract_response_text(response)
            if not text_content:
                logger.error(
                    "[%s] OpenAI response did not contain text output. Raw response: %s",
                    context,
                    _serialize_response_for_log(response),
                )
                raise RuntimeError("OpenAI response did not contain text output")

            return {
                "_text": text_content,
                "_input_tokens": input_tokens,
                "_output_tokens": output_tokens,
            }

        except RateLimitError as exc:
            logger.warning(
                "[%s] Rate limited (attempt %d/%d). Waiting %.1fs...",
                context,
                attempt,
                max_retries,
                backoff,
            )
            last_error = exc
            time.sleep(backoff)
            backoff *= 2
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning(
                "[%s] Transient OpenAI error (attempt %d/%d): %s. Retrying in %.1fs...",
                context,
                attempt,
                max_retries,
                exc,
                backoff,
            )
            last_error = exc
            time.sleep(backoff)
            backoff *= 2
        except APIStatusError as exc:
            if exc.status_code in {408, 409, 429, 500, 502, 503, 504}:
                logger.warning(
                    "[%s] OpenAI API status %s (attempt %d/%d). Retrying in %.1fs...",
                    context,
                    exc.status_code,
                    attempt,
                    max_retries,
                    backoff,
                )
                last_error = exc
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except Exception as exc:
            error_str = str(exc).lower()
            if "timeout" in error_str or "connection" in error_str or "network" in error_str:
                logger.warning(
                    "[%s] Transient error (attempt %d/%d): %s. Retrying in %.1fs...",
                    context,
                    attempt,
                    max_retries,
                    exc,
                    backoff,
                )
                last_error = exc
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    raise RuntimeError(
        f"[{context}] All {max_retries} retries exhausted. Last error: {last_error}"
    )


async def run_realtime_mode(
    workspace: Path,
    rubric: Rubric,
    model: str,
    workers: int,
    resume: bool,
) -> None:
    """Execute real-time scoring mode."""
    ir_dir = workspace / "ir"
    scores_dir = workspace / "scores"
    progress_path = workspace / "progress.json"

    # Discover IR files
    ir_files = sorted(ir_dir.glob("*.json"))
    all_ids = [p.stem for p in ir_files]
    id_to_path = {p.stem: p for p in ir_files}

    if not all_ids:
        logger.error("No IR files found in %s", ir_dir)
        return

    logger.info("Found %d IR files in %s", len(all_ids), ir_dir)

    # Resume or initialize progress
    progress: Progress
    if resume and progress_path.exists():
        loaded = load_progress(progress_path)
        if loaded is not None:
            progress = loaded
            logger.info(
                "Resuming batch: %d completed, %d failed, %d pending",
                progress.completed,
                progress.failed,
                progress.pending,
            )
        else:
            resume = False

    if not resume:
        # Randomize order (anti-position-bias)
        processing_order = list(all_ids)
        random.shuffle(processing_order)

        progress = Progress(
            batch_id=workspace.name,
            rubric_id=rubric.id,
            mode="real-time",
            started_at=_now_iso(),
            last_updated=_now_iso(),
            total=len(all_ids),
            pending=len(all_ids),
            pending_ids=list(processing_order),
            processing_order=list(processing_order),
        )

    # Determine which IDs to process
    completed_set = set(progress.completed_ids)
    failed_map = {fi.id: fi for fi in progress.failed_ids}

    to_process: list[str] = []
    for sid in progress.processing_order:
        if sid in completed_set:
            continue
        if sid in failed_map and failed_map[sid].attempts >= MAX_RETRIES:
            continue
        if sid in id_to_path:
            to_process.append(sid)

    logger.info("Submissions to process: %d", len(to_process))

    if not to_process:
        logger.info("Nothing to process - batch complete")
        _print_summary(progress, batch_mode=False)
        return

    # Check API key
    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or _config_value("openai", "api_key")
    )
    if not api_key:
        logger.error(
            "OPENAI_API_KEY not set. Configure it in the environment or grader-config.yaml"
        )
        sys.exit(1)

    semaphore = asyncio.Semaphore(workers)

    # Accumulate stats for summary
    total_input_tokens = 0
    total_output_tokens = 0

    # Process each submission
    for sid in to_process:
        ir_path = id_to_path.get(sid)
        if ir_path is None:
            logger.warning("IR file not found for %s - skipping", sid)
            continue

        try:
            ir = load_ir_file(ir_path)

            # Check if gate failed with on_fail=fail
            gate_failed = False
            for gate in ir.get("gate_results", []):
                if not gate.get("passed", True) and gate.get("on_fail") == "fail":
                    gate_failed = True
                    break

            if gate_failed:
                logger.info("Skipping %s - gate FAILED (on_fail=fail)", sid)
                _record_failure(
                    progress, sid, "Gate check failed (on_fail=fail)", 0
                )
                save_progress(progress_path, progress)
                continue

            result = await score_one_submission(
                model=model,
                rubric=rubric,
                workspace=workspace,
                ir=ir,
                semaphore=semaphore,
            )

            # Save score file atomically
            save_score_file(scores_dir, sid, result.score_data)

            # Update progress
            progress.completed_ids.append(sid)
            if sid in progress.pending_ids:
                progress.pending_ids.remove(sid)
            progress.completed = len(progress.completed_ids)
            progress.pending = len(progress.pending_ids)

            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens

            # Update running stats
            progress.stats = {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost_usd": estimate_cost(
                    total_input_tokens, total_output_tokens, batch_mode=False
                ),
            }

            save_progress(progress_path, progress)

            logger.info(
                "[%d/%d] Scored %s - weighted_total=%.2f (%dms)",
                progress.completed,
                progress.total,
                sid,
                result.score_data.get("weighted_total", 0),
                result.duration_ms,
            )

        except Exception as exc:
            logger.error("Failed to score %s: %s", sid, exc, exc_info=True)
            attempt_count = failed_map.get(sid, FailedItem(sid, "", 0)).attempts + 1
            _record_failure(progress, sid, str(exc), attempt_count)
            save_progress(progress_path, progress)

    # Final save
    save_progress(progress_path, progress)
    _print_summary(progress, batch_mode=False)


def _record_failure(
    progress: Progress,
    student_id: str,
    error: str,
    attempts: int,
) -> None:
    """Record a failure in the progress tracker."""
    # Remove from pending if present
    if student_id in progress.pending_ids:
        progress.pending_ids.remove(student_id)

    # Update or add failed item
    existing = None
    for fi in progress.failed_ids:
        if fi.id == student_id:
            existing = fi
            break

    if existing is not None:
        existing.error = error
        existing.attempts = attempts
        existing.last_attempt = _now_iso()
    else:
        progress.failed_ids.append(
            FailedItem(
                id=student_id,
                error=error,
                attempts=attempts,
                last_attempt=_now_iso(),
            )
        )

    progress.failed = len(progress.failed_ids)
    progress.pending = len(progress.pending_ids)


# ---------------------------------------------------------------------------
# Batch API mode
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _print_summary(progress: Progress, batch_mode: bool) -> None:
    """Log a batch completion summary."""
    logger.info("=" * 60)
    logger.info("BATCH SCORING SUMMARY")
    logger.info("=" * 60)
    logger.info("Batch ID:   %s", progress.batch_id)
    logger.info("Rubric:     %s", progress.rubric_id)
    logger.info("Mode:       %s", progress.mode)
    logger.info("Total:      %d", progress.total)
    logger.info("Completed:  %d", progress.completed)
    logger.info("Failed:     %d", progress.failed)
    logger.info("Pending:    %d", progress.pending)
    if progress.completed > 0:
        cost = progress.stats.get("total_cost_usd", 0)
        logger.info("Est. cost:  $%.4f", cost)

    if progress.failed_ids:
        logger.info("-" * 60)
        logger.info("FAILED SUBMISSIONS:")
        for fi in progress.failed_ids:
            if isinstance(fi, FailedItem):
                logger.info("  %s - %s (attempts: %d)", fi.id, fi.error, fi.attempts)
            elif isinstance(fi, dict):
                logger.info(
                    "  %s - %s (attempts: %d)",
                    fi.get("id", "?"),
                    fi.get("error", "?"),
                    fi.get("attempts", 0),
                )

    logger.info("=" * 60)


def export_timestamped_excel(workspace: Path) -> Path | None:
    """Export current scores to a new timestamped Excel workbook."""
    scores_dir = workspace / "scores"
    mapping_path = workspace / "student-mapping.csv"
    reports_dir = workspace / "reports"

    scores = load_scores(scores_dir)
    if not scores:
        logger.warning("Skipping Excel export because no scores were found in %s", scores_dir)
        return None

    mapping = load_mapping(mapping_path)
    grade_df = build_grade_table(scores, mapping)
    stats = build_statistics(grade_df, scores)
    detail_df = build_detail_table(scores, mapping)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = reports_dir / f"grades-{timestamp}.xlsx"
    write_excel(grade_df, stats, detail_df, output_path)
    return output_path


def generate_default_stats_report(workspace: Path) -> Path | None:
    """Generate the default post-batch statistics report."""
    try:
        import stats as stats_module
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping statistics report: failed to import stats module (%s)", exc)
        return None

    try:
        records = stats_module.load_scores(workspace)
        if not records:
            logger.warning("Skipping statistics report because no score records were found")
            return None

        processing_order = stats_module.load_processing_order(workspace)
        dist = stats_module.analyze_distribution(records)

        dim_totals: dict[str, list[int]] = {}
        dim_names: dict[str, str] = {}
        for record in records:
            for criterion_id, score in record.dimension_scores.items():
                dim_totals.setdefault(criterion_id, []).append(score)

        for path in sorted((workspace / "scores").glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for dim in data.get("dimension_scores", []):
                    criterion_id = dim.get("criterion_id", "")
                    if criterion_id:
                        dim_names[criterion_id] = dim.get("criterion_name", criterion_id)
                break
            except Exception:
                continue

        dim_means = {
            dim_names.get(criterion_id, criterion_id): round(sum(scores) / len(scores), 2)
            for criterion_id, scores in dim_totals.items()
            if scores
        }
        confidences = [record.confidence for record in records]
        total = len(confidences)
        conf_stats = {
            "mean": sum(confidences) / total if total else 0,
            "low_count": sum(1 for value in confidences if value < 0.6),
            "low_pct": sum(1 for value in confidences if value < 0.6) / total * 100 if total else 0,
            "med_count": sum(1 for value in confidences if 0.6 <= value < 0.8),
            "med_pct": sum(1 for value in confidences if 0.6 <= value < 0.8) / total * 100 if total else 0,
            "high_count": sum(1 for value in confidences if value >= 0.8),
            "high_pct": sum(1 for value in confidences if value >= 0.8) / total * 100 if total else 0,
        }

        biases: list[Any] = []
        length_bias = stats_module.detect_length_bias(records)
        if length_bias:
            biases.append(length_bias)
        position_bias = stats_module.detect_position_bias(records, processing_order)
        if position_bias:
            biases.append(position_bias)
        biases.extend(stats_module.detect_dimension_coupling(records))

        report = stats_module.generate_report(dist, biases, dim_means, conf_stats)
        output_path = workspace / "reports" / "statistics.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        if dist.concentration_warning:
            logger.warning("Statistics warning: scores are overly concentrated at a single level")
        if dist.skewness_warning:
            logger.warning("Statistics warning: score distribution skewness exceeded threshold")
        detected_biases = [bias.bias_type for bias in biases if getattr(bias, "detected", False)]
        if detected_biases:
            logger.warning("Statistics warning: detected %s", ", ".join(detected_biases))

        return output_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("Statistics report generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch-score preprocessed homework submissions against a Rubric.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Real-time scoring with default 5 workers
  python batch_score.py workspace/batch-001 --rubric my-rubric.yaml

  # Resume an interrupted run
  python batch_score.py workspace/batch-001 --rubric my-rubric.yaml --resume

  # Use a dedicated runtime config for an isolated batch
  python batch_score.py --config grader-config.cqupt-final.yaml
""",
    )
    parser.add_argument(
        "workspace",
        type=Path,
        nargs="?",
        help="Workspace directory (must contain ir/ subdirectory with IR JSON files)",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        help="Path to the Rubric YAML file",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers. Default: {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted batch from progress.json checkpoint",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the scoring model (default: env SCORING_MODEL or "
        f"{DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional runtime config YAML. Defaults to env GRADER_CONFIG_PATH "
        "or grader-config.yaml in the project root.",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> None:
    """Async entry point."""
    _set_runtime_config_path(args.config)

    configured_workspace = _resolve_configured_path(
        _config_value("grading", "workspace_path")
    )
    configured_rubric = _resolve_configured_path(
        _config_value("grading", "rubric_path")
    )

    workspace: Path | None = args.workspace or configured_workspace
    rubric_path: Path | None = args.rubric or configured_rubric
    workers: int = args.workers

    # Resolve model
    model = (
        args.model
        or os.environ.get("SCORING_MODEL", "").strip()
        or _config_value("openai", "model")
        or DEFAULT_MODEL
    )

    if workspace is None:
        logger.error(
            "Workspace not set. Pass it on the command line or configure grading.workspace_path "
            "in the resolved runtime config file"
        )
        sys.exit(1)

    if rubric_path is None:
        logger.error(
            "Rubric path not set. Pass --rubric or configure grading.rubric_path in "
            "the resolved runtime config file"
        )
        sys.exit(1)

    # Validate workspace
    ir_dir = workspace / "ir"
    if not ir_dir.is_dir():
        logger.error("IR directory not found: %s", ir_dir)
        sys.exit(1)

    # Ensure output directories exist
    (workspace / "scores").mkdir(parents=True, exist_ok=True)
    (workspace / "logs").mkdir(parents=True, exist_ok=True)

    # Add file handler for logging
    log_file = workspace / "logs" / "scoring.log"
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

    # Load and validate rubric
    try:
        rubric = load_rubric(rubric_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Rubric error: %s", exc)
        sys.exit(1)

    logger.info(
        "Starting batch scoring - model=%s, workers=%d",
        model,
        workers,
    )

    # Always use real-time mode
    await run_realtime_mode(
        workspace=workspace,
        rubric=rubric,
        model=model,
        workers=workers,
        resume=args.resume,
    )

    excel_path = export_timestamped_excel(workspace)
    if excel_path is not None:
        logger.info("Generated Excel report: %s", excel_path)

    stats_path = generate_default_stats_report(workspace)
    if stats_path is not None:
        logger.info("Generated statistics report: %s", stats_path)


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

