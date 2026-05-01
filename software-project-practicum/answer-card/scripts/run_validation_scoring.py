from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image

from common import (
    ANSWER_CARD_ROOT,
    extract_json_object,
    iter_image_files,
    load_grader_config,
    load_template_config,
    load_yaml,
    paper_id_from_path,
    phase1_workspace_path,
    pil_to_data_url,
    read_image,
    save_json,
)
from extract_scanned_scores import create_red_mask, normalize_scan

logger = logging.getLogger(__name__)

DEFAULT_UNMODIFIED_INPUT_DIR = (
    ANSWER_CARD_ROOT.parent / "workspace" / "practicum-batch" / "raw" / "软件需求答题卡（未修改）"
).resolve()
DEFAULT_OUTPUT_DIR = (ANSWER_CARD_ROOT / "workspace" / "validation-run").resolve()

SAMPLE_DEBUG_IDS = [
    "2023214327_王志怡",
    "2023214329_李丹阳",
    "2023214345_张翼",
]

QUESTION_KEYS = [str(i) for i in range(26, 34)]
FILL_KEYS = [str(i) for i in range(21, 26)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run validation scoring on unmodified answer cards.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--grader-config", type=Path, default=None, help="Optional practicum grader-config.yaml path.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_UNMODIFIED_INPUT_DIR, help="Unmodified answer-card directory.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument(
        "--standard-answers",
        type=Path,
        default=ANSWER_CARD_ROOT / "configs" / "standard_answers.yaml",
        help="Standard answers yaml path.",
    )
    parser.add_argument(
        "--scoring-rubric",
        type=Path,
        default=ANSWER_CARD_ROOT / "configs" / "scoring_rubric.yaml",
        help="Subjective scoring rubric yaml path.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--paper-ids", type=str, default="", help="Comma-separated paper ids.")
    parser.add_argument("--split-file", type=Path, default=None, help="Optional split file containing paper ids.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N selected papers.")
    parser.add_argument("--model", type=str, default=None, help="Override the model from grader-config.yaml.")
    return parser.parse_args()


def build_openai_client(grader_config: dict[str, Any]) -> tuple[OpenAI, str]:
    openai_cfg = grader_config.get("openai", {}) or {}
    api_key = str(openai_cfg.get("api_key", "")).strip()
    base_url = str(openai_cfg.get("base_url", "")).strip() or None
    model = str(openai_cfg.get("model", "")).strip() or "gpt-5.4"
    return OpenAI(api_key=api_key, base_url=base_url), model


def read_id_list(path: Path) -> list[str]:
    ids: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            text = line.strip().lstrip("\ufeff")
            if text:
                ids.append(text)
    return ids


def resolve_selected_ids(args: argparse.Namespace) -> list[str]:
    ids: list[str] = []
    if args.paper_ids:
        ids.extend([item.strip() for item in args.paper_ids.split(",") if item.strip()])
    if args.split_file:
        ids.extend(read_id_list(args.split_file.resolve()))
    if not ids:
        ids = list(SAMPLE_DEBUG_IDS)
    seen: set[str] = set()
    ordered: list[str] = []
    for paper_id in ids:
        if paper_id not in seen:
            ordered.append(paper_id)
            seen.add(paper_id)
    if args.limit:
        ordered = ordered[: args.limit]
    return ordered


def index_image_files(input_dir: Path) -> dict[str, Path]:
    return {paper_id_from_path(path): path for path in iter_image_files(input_dir)}


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    value = str(text).strip().lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[，,。.;；:：()（）【】\[\]{}“”\"'、·\-]", "", value)
    return value


def normalize_choice_answer(value: Any, allowed: set[str]) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"", "NULL", "NONE", "UNKNOWN"}:
        return None
    return text if text in allowed else None


def objective_answer_map(standard_answers: dict[str, Any], section_key: str) -> dict[str, str]:
    return {
        str(qid): str(answer).strip().upper()
        for qid, answer in ((standard_answers.get(section_key, {}) or {}).get("answers", {}) or {}).items()
        if answer is not None
    }


def fill_answer_map(standard_answers: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return (standard_answers.get("fill_blank", {}) or {}).get("answers", {}) or {}


def build_subjective_prompt_spec(scoring_rubric: dict[str, Any]) -> dict[str, Any]:
    questions = scoring_rubric.get("subjective_questions", {}) or {}
    spec: dict[str, Any] = {}
    for qid, item in questions.items():
        question_spec: dict[str, Any] = {
            "title": item.get("title", ""),
            "max_score": item.get("max_score"),
            "grading_strategy": item.get("grading_strategy"),
        }
        if "scoring_points" in item:
            question_spec["scoring_points"] = [
                {
                    "id": point.get("id"),
                    "description": point.get("description"),
                    "score": point.get("score"),
                }
                for point in item.get("scoring_points", []) or []
            ]
        if "accepted_methods" in item:
            question_spec["accepted_methods"] = item.get("accepted_methods", [])
            question_spec["scoring_policy"] = item.get("scoring_policy", {})
        if "accepted_types" in item:
            question_spec["accepted_types"] = item.get("accepted_types", [])
            question_spec["scoring_policy"] = item.get("scoring_policy", {})
        spec[str(qid)] = question_spec
    return spec


def crop_single_choice_area(normalized: Image.Image) -> dict[str, Image.Image]:
    width, height = normalized.size
    red_mask = create_red_mask(normalized)
    box = (
        int(width * 0.015),
        int(height * 0.115),
        int(width * 0.495),
        int(height * 0.225),
    )
    return {"original": normalized.crop(box), "red_mask": red_mask.crop(box)}


def crop_true_false_area(normalized: Image.Image) -> dict[str, Image.Image]:
    width, height = normalized.size
    red_mask = create_red_mask(normalized)
    box = (
        int(width * 0.015),
        int(height * 0.205),
        int(width * 0.495),
        int(height * 0.325),
    )
    original = normalized.crop(box)
    mask = red_mask.crop(box)
    enlarged_size = (original.width * 2, original.height * 2)
    return {
        "original": original,
        "red_mask": mask,
        "enlarged": original.resize(enlarged_size),
        "red_mask_enlarged": mask.resize(enlarged_size),
    }


def crop_true_false_row_images(normalized: Image.Image) -> dict[str, dict[str, Image.Image]]:
    area = crop_true_false_area(normalized)
    original = area["original"]
    mask = area["red_mask"]
    width, height = original.size
    top_box = (0, 0, width, int(height * 0.58))
    bottom_box = (0, int(height * 0.36), width, height)

    def build_variants(box: tuple[int, int, int, int]) -> dict[str, Image.Image]:
        row_original = original.crop(box)
        row_mask = mask.crop(box)
        enlarged_size = (row_original.width * 2, row_original.height * 2)
        return {
            "original": row_original,
            "red_mask": row_mask,
            "enlarged": row_original.resize(enlarged_size),
            "red_mask_enlarged": row_mask.resize(enlarged_size),
        }

    return {
        "odd": build_variants(top_box),
        "even": build_variants(bottom_box),
    }


def crop_true_false_question_images(normalized: Image.Image) -> dict[str, dict[str, Image.Image]]:
    area = crop_true_false_area(normalized)
    original = area["original"]
    mask = area["red_mask"]
    width, height = original.size
    col_left = int(width * 0.03)
    col_right = int(width * 0.97)
    row_top = int(height * 0.08)
    row_bottom = int(height * 0.90)
    row_height = row_bottom - row_top
    upper_y0 = row_top
    upper_y1 = row_top + int(row_height * 0.42)
    lower_y0 = row_top + int(row_height * 0.44)
    lower_y1 = row_bottom

    question_images: dict[str, dict[str, Image.Image]] = {}
    odd_ids = [11, 13, 15, 17, 19]
    even_ids = [12, 14, 16, 18, 20]

    def build_question_variant(box: tuple[int, int, int, int]) -> dict[str, Image.Image]:
        question_original = original.crop(box)
        question_mask = mask.crop(box)
        enlarged_size = (question_original.width * 3, question_original.height * 3)
        return {
            "original": question_original,
            "red_mask": question_mask,
            "enlarged": question_original.resize(enlarged_size),
            "red_mask_enlarged": question_mask.resize(enlarged_size),
        }

    for index, qid in enumerate(odd_ids):
        x0 = col_left + int((col_right - col_left) * index / 5)
        x1 = col_left + int((col_right - col_left) * (index + 1) / 5)
        question_images[str(qid)] = build_question_variant((x0, upper_y0, x1, upper_y1))

    for index, qid in enumerate(even_ids):
        x0 = col_left + int((col_right - col_left) * index / 5)
        x1 = col_left + int((col_right - col_left) * (index + 1) / 5)
        question_images[str(qid)] = build_question_variant((x0, lower_y0, x1, lower_y1))

    return question_images


def crop_fill_blank_area(normalized: Image.Image) -> dict[str, Image.Image]:
    width, height = normalized.size
    red_mask = create_red_mask(normalized)
    box = (
        int(width * 0.01),
        int(height * 0.235),
        int(width * 0.50),
        int(height * 0.335),
    )
    return {"original": normalized.crop(box), "red_mask": red_mask.crop(box)}


def subjective_full_image(normalized: Image.Image) -> dict[str, Image.Image]:
    return {"original": normalized}


def resolve_prompt_images(prompt: list[dict[str, Any]], images: dict[str, Image.Image]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in prompt:
        if item.get("type") != "image_url":
            resolved.append(item)
            continue
        url = str(item.get("image_url", {}).get("url", ""))
        key = url.replace("__IMAGE__:", "")
        if key in images:
            resolved.append({"type": "image_url", "image_url": {"url": pil_to_data_url(images[key])}})
        else:
            resolved.append(item)
    return resolved


def objective_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "读取未批改答题卡中的客观题作答区域。"
                "只识别学生自己的选择结果，不要根据任何教师红笔推断。"
                "单选题1-10只允许返回A/B/C/D/null；判断题11-20只允许返回T/F/null。"
                "请只返回JSON："
                "{"
                '"single_choice":{"1":{"student_answer":"A|B|C|D|null","evidence":"..."},...},'
                '"true_false":{"11":{"student_answer":"T|F|null","evidence":"..."},...},'
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
    ]


def single_choice_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "读取未批改答题卡中的单选题1-10作答区域。"
                "只识别学生自己的填涂结果，不要参考任何教师批注。"
                "每题只允许返回A/B/C/D/null。"
                "如果看见多个选项、擦改痕迹明显或无法确认，就返回null。"
                "请只返回JSON："
                "{"
                '"single_choice":{"1":{"student_answer":"A|B|C|D|null","evidence":"..."},...},'
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
    ]


def true_false_row_prompt(question_ids: list[int], row_label: str) -> list[dict[str, Any]]:
    ordered = ",".join(str(qid) for qid in question_ids)
    fields = ",".join(
        f'"{qid}":{{"student_answer":"T|F|null","evidence":"..."}}' for qid in question_ids
    )
    return [
        {
            "type": "text",
            "text": (
                f"读取未批改答题卡中判断题的{row_label}。"
                f"这一行从左到右依次只包含这些题号：{ordered}。"
                "每一题只有左右两个候选位置，必须逐题比较左右两个位置谁被学生填涂得更明显。"
                "左侧对应T，右侧对应F。"
                "不要把另一行的题号混进来，也不要漏题。"
                "必须按这一行从左到右逐题独立判断。"
                "只有在右侧比左侧更明显时才返回F；只有在左侧比右侧更明显时才返回T；否则返回null。"
                "evidence里要明确写出“左侧(T)更黑”、“右侧(F)更黑”或“无法确认”。"
                "请只返回JSON："
                "{"
                f'"true_false":{{{fields}}},'
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:enlarged"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask_enlarged"}},
    ]


def true_false_area_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "读取未批改答题卡中的判断题11-20作答区域。"
                "这一块题目按两排排布：上排通常是11、13、15、17、19，下排通常是12、14、16、18、20。"
                "每一题都只有左右两个候选位置，左侧对应T，右侧对应F。"
                "必须逐题判断，不要整列默认成同一个答案。"
                "只有在左侧更明显时返回T，右侧更明显时返回F，否则返回null。"
                "请只返回JSON："
                "{"
                '"true_false":{"11":{"student_answer":"T|F|null","evidence":"..."},...,"20":{"student_answer":"T|F|null","evidence":"..."}},'
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:enlarged"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask_enlarged"}},
    ]


def true_false_question_prompt(question_id: int) -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                f"读取未批改答题卡中的判断题第{question_id}题小块图像。"
                "这张图里只看这一题。"
                "左侧候选位置对应T，右侧候选位置对应F。"
                "请比较左右两个位置谁被学生填涂得更明显。"
                "如果左侧更明显返回T，右侧更明显返回F，否则返回null。"
                "evidence要明确写出‘左侧(T)更黑’、‘右侧(F)更黑’或‘无法确认’。"
                "请只返回JSON："
                "{"
                f'"question":"{question_id}","student_answer":"T|F|null","evidence":"..."'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:enlarged"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask_enlarged"}},
    ]


def fill_blank_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "读取未批改答题卡中的填空题21-25。"
                "只提取学生填写的答案文本，不要代替评分。"
                "如果看不清可返回null。"
                "请只返回JSON："
                "{"
                '"answers":{'
                '"21":{"text":"string|null","evidence":"..."},'
                '"22":{"text":"string|null","evidence":"..."},'
                '"23":{"text":"string|null","evidence":"..."},'
                '"24":{"text":"string|null","evidence":"..."},'
                '"25":{"text":"string|null","evidence":"..."}'
                "},"
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
    ]


def subjective_prompt(scoring_rubric: dict[str, Any]) -> list[dict[str, Any]]:
    subjective_spec = build_subjective_prompt_spec(scoring_rubric)
    return [
        {
            "type": "text",
            "text": (
                "对未批改答题卡中的主观题26-33评分。"
                "必须根据学生作答内容评分，不得参考教师批注。"
                "图示题必须看图，不要只靠OCR。"
                "评分标准如下："
                f"{json.dumps(subjective_spec, ensure_ascii=False)}"
                "请只返回JSON："
                "{"
                '"subjective":{"26":{"score":number,"evidence":"..."},...,"33":{"score":number,"evidence":"..."}},'
                '"review_required":true|false,'
                '"review_reasons":[string]'
                "}"
            ),
        },
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
    ]


def call_model(client: OpenAI, model: str, prompt: list[dict[str, Any]], images: dict[str, Image.Image]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": resolve_prompt_images(prompt, images)}],
    )
    text = response.choices[0].message.content or ""
    return extract_json_object(text)


def detect_true_false_by_fill(normalized: Image.Image) -> tuple[dict[str, Any], list[str]]:
    images_by_question = crop_true_false_question_images(normalized)
    results: dict[str, Any] = {}
    notes = ["????????????????????????"]

    for qid in range(11, 21):
        image = images_by_question[str(qid)]["original"].convert("L")
        width, height = image.size

        y0 = int(height * 0.18)
        y1 = int(height * 0.82)
        left_x0 = int(width * 0.26)
        left_x1 = int(width * 0.49)
        right_x0 = int(width * 0.56)
        right_x1 = int(width * 0.79)

        left_crop = image.crop((left_x0, y0, left_x1, y1))
        right_crop = image.crop((right_x0, y0, right_x1, y1))

        def darkness_score(crop: Image.Image) -> float:
            pixels = list(crop.getdata())
            if not pixels:
                return 0.0
            score = 0.0
            for value in pixels:
                if value < 210:
                    score += (255 - value) / 255.0
            return score

        left_score = darkness_score(left_crop)
        right_score = darkness_score(right_crop)
        diff = abs(left_score - right_score)
        stronger = max(left_score, right_score)

        if stronger < 8.0 or diff < 2.2:
            answer = None
            evidence = f"????????????????left={left_score:.2f}, right={right_score:.2f}"
        elif left_score > right_score:
            answer = "T"
            evidence = f"??(T)???left={left_score:.2f}, right={right_score:.2f}"
        else:
            answer = "F"
            evidence = f"??(F)???left={left_score:.2f}, right={right_score:.2f}"

        results[str(qid)] = {
            "student_answer": answer,
            "evidence": evidence,
        }

    return results, notes


def extract_objective_answers(
    client: OpenAI,
    model: str,
    normalized: Image.Image,
) -> dict[str, Any]:
    single_payload = call_model(client, model, single_choice_prompt(), crop_single_choice_area(normalized))
    tf_raw, tf_notes = detect_true_false_by_fill(normalized)
    single_raw = single_payload.get("single_choice", {}) or {}

    notes = [str(item).strip() for item in single_payload.get("notes", []) if str(item).strip()]
    notes.extend(tf_notes)

    tf_answers = [
        normalize_choice_answer((tf_raw.get(str(qid), {}) or {}).get("student_answer"), {"T", "F"})
        for qid in range(11, 21)
    ]
    unique_tf_answers = {item for item in tf_answers if item}
    if len(unique_tf_answers) == 1 and len([item for item in tf_answers if item is not None]) >= 8:
        notes.append("???11-20??????????????????????")

    return {
        "single_choice": {
            str(qid): {
                "student_answer": normalize_choice_answer(
                    (single_raw.get(str(qid), {}) or {}).get("student_answer"), {"A", "B", "C", "D"}
                ),
                "evidence": str((single_raw.get(str(qid), {}) or {}).get("evidence", "")).strip(),
            }
            for qid in range(1, 11)
        },
        "true_false": {
            str(qid): {
                "student_answer": normalize_choice_answer((tf_raw.get(str(qid), {}) or {}).get("student_answer"), {"T", "F"}),
                "evidence": str((tf_raw.get(str(qid), {}) or {}).get("evidence", "")).strip(),
            }
            for qid in range(11, 21)
        },
        "notes": notes,
    }
def extract_fill_blank_answers(
    client: OpenAI,
    model: str,
    normalized: Image.Image,
) -> dict[str, Any]:
    payload = call_model(client, model, fill_blank_prompt(), crop_fill_blank_area(normalized))
    raw_answers = payload.get("answers", {}) or {}
    return {
        "answers": {
            qid: {
                "text": (str((raw_answers.get(qid, {}) or {}).get("text", "")).strip() or None),
                "evidence": str((raw_answers.get(qid, {}) or {}).get("evidence", "")).strip(),
            }
            for qid in FILL_KEYS
        },
        "notes": [str(item).strip() for item in payload.get("notes", []) if str(item).strip()],
    }


def extract_subjective_scores(
    client: OpenAI,
    model: str,
    normalized: Image.Image,
    scoring_rubric: dict[str, Any],
) -> dict[str, Any]:
    payload = call_model(client, model, subjective_prompt(scoring_rubric), subjective_full_image(normalized))
    raw_subjective = payload.get("subjective", {}) or {}
    return {
        "subjective": {
            qid: {
                "score": (raw_subjective.get(qid, {}) or {}).get("score"),
                "evidence": str((raw_subjective.get(qid, {}) or {}).get("evidence", "")).strip(),
            }
            for qid in QUESTION_KEYS
        },
        "review_required": bool(payload.get("review_required")),
        "review_reasons": [str(item).strip() for item in payload.get("review_reasons", []) if str(item).strip()],
    }


def score_objective_section(
    payload: dict[str, Any],
    answer_key: dict[str, str],
    per_question_score: float,
    allowed: set[str],
) -> tuple[dict[str, Any], float]:
    results: dict[str, Any] = {}
    total = 0.0
    for qid, correct in answer_key.items():
        raw_item = payload.get(qid, {}) or {}
        student_answer = normalize_choice_answer(raw_item.get("student_answer"), allowed)
        is_correct = student_answer == correct if student_answer is not None else None
        score = per_question_score if is_correct else 0.0
        if is_correct:
            total += score
        results[qid] = {
            "student_answer": student_answer,
            "correct_answer": correct,
            "correct": is_correct,
            "score": score,
            "evidence": str(raw_item.get("evidence", "")).strip(),
        }
    return results, total


def score_fill_blank_section(
    payload: dict[str, Any],
    standard_answers: dict[str, Any],
) -> tuple[dict[str, Any], float, list[str]]:
    fill_specs = fill_answer_map(standard_answers)
    results: dict[str, Any] = {}
    total = 0.0
    review_reasons: list[str] = []
    for qid, spec in fill_specs.items():
        raw_item = payload.get(str(qid), {}) or {}
        text = str(raw_item.get("text", "")).strip() or None
        normalized = normalize_text(text)
        accepted_texts = [normalize_text(spec.get("canonical"))]
        accepted_texts.extend(normalize_text(alias) for alias in spec.get("aliases", []) or [])
        matched = bool(normalized and normalized in {item for item in accepted_texts if item})
        score = 2.0 if matched else 0.0
        if not matched and text:
            review_reasons.append(f"Q{qid} fill_blank_unmatched")
        total += score
        results[str(qid)] = {
            "text": text,
            "accepted": matched,
            "score": score,
            "match_type": "规则命中" if matched else "未命中",
            "canonical_answer": spec.get("canonical"),
            "evidence": str(raw_item.get("evidence", "")).strip(),
        }
    return results, total, review_reasons


def score_subjective_section(payload: dict[str, Any], scoring_rubric: dict[str, Any]) -> tuple[dict[str, Any], float]:
    rubric_questions = scoring_rubric.get("subjective_questions", {}) or {}
    results: dict[str, Any] = {}
    total = 0.0
    for qid, rubric in rubric_questions.items():
        raw_item = payload.get(str(qid), {}) or {}
        raw_score = raw_item.get("score")
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        max_score = float(rubric.get("max_score", 0))
        score = max(0.0, min(score, max_score))
        score = round(score * 2) / 2
        total += score
        results[str(qid)] = {
            "score": score,
            "evidence": str(raw_item.get("evidence", "")).strip(),
        }
    return results, total


def build_result(
    paper_id: str,
    image_path: Path,
    extracted_payload: dict[str, Any],
    standard_answers: dict[str, Any],
    scoring_rubric: dict[str, Any],
) -> dict[str, Any]:
    single_results, single_score = score_objective_section(
        extracted_payload.get("objective", {}).get("single_choice", {}) or {},
        objective_answer_map(standard_answers, "single_choice"),
        float(((standard_answers.get("question_types", {}) or {}).get("single_choice", {}) or {}).get("per_question_score", 2)),
        {"A", "B", "C", "D"},
    )
    tf_results, tf_score = score_objective_section(
        extracted_payload.get("objective", {}).get("true_false", {}) or {},
        objective_answer_map(standard_answers, "true_false"),
        float(((standard_answers.get("question_types", {}) or {}).get("true_false", {}) or {}).get("per_question_score", 1)),
        {"T", "F"},
    )
    fill_results, fill_score, fill_review_reasons = score_fill_blank_section(
        extracted_payload.get("fill_blank", {}).get("answers", {}) or {}, standard_answers
    )
    subjective_results, _ = score_subjective_section(
        extracted_payload.get("subjective", {}).get("subjective", {}) or {}, scoring_rubric
    )

    short_answer_score = sum(subjective_results[qid]["score"] for qid in ["26", "27", "28", "29"])
    comprehensive_score = sum(subjective_results[qid]["score"] for qid in ["30", "31", "32", "33"])
    system_total = single_score + tf_score + fill_score + short_answer_score + comprehensive_score

    review_reasons: list[str] = []
    review_reasons.extend(extracted_payload.get("objective", {}).get("notes", []) or [])
    review_reasons.extend(extracted_payload.get("fill_blank", {}).get("notes", []) or [])
    review_reasons.extend(fill_review_reasons)
    review_reasons.extend(extracted_payload.get("subjective", {}).get("review_reasons", []) or [])
    review_required = bool(extracted_payload.get("subjective", {}).get("review_required")) or bool(review_reasons)

    evidence_parts = [item["evidence"] for item in subjective_results.values() if item.get("evidence")]
    evidence_parts.extend(item["evidence"] for item in fill_results.values() if item.get("evidence"))

    return {
        "paper_id": paper_id,
        "source_image": str(image_path),
        "system_total": round(system_total, 2),
        "section_scores": {
            "single_choice": round(single_score, 2),
            "true_false": round(tf_score, 2),
            "fill_blank": round(fill_score, 2),
            "short_answer": round(short_answer_score, 2),
            "comprehensive": round(comprehensive_score, 2),
        },
        "question_scores": {qid: subjective_results[qid]["score"] for qid in subjective_results},
        "review_required": review_required,
        "review_reason": " | ".join(str(item).strip() for item in review_reasons if str(item).strip()),
        "evidence": " | ".join(evidence_parts)[:4000],
        "details": {
            "single_choice": single_results,
            "true_false": tf_results,
            "fill_blank": fill_results,
            "subjective": subjective_results,
        },
        "extracted": extracted_payload,
    }


def load_teacher_truth(workspace: Path, paper_id: str) -> dict[str, Any] | None:
    path = workspace / "parsed" / f"{paper_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_debug_split(output_dir: Path, paper_ids: list[str]) -> Path:
    split_path = output_dir / "debug_sample_ids.txt"
    split_path.write_text("\n".join(paper_ids) + "\n", encoding="utf-8")
    return split_path


def process_one(
    client: OpenAI,
    model: str,
    image_path: Path,
    template_config: dict[str, Any],
    standard_answers: dict[str, Any],
    scoring_rubric: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    paper_id = paper_id_from_path(image_path)
    image = read_image(image_path)
    normalized, normalize_debug = normalize_scan(image, template_config.get("template", {}) or {})

    extracted_payload = {
        "paper_id": paper_id,
        "source_image": str(image_path),
        "normalization": normalize_debug,
        "objective": extract_objective_answers(client, model, normalized),
        "fill_blank": extract_fill_blank_answers(client, model, normalized),
        "subjective": extract_subjective_scores(client, model, normalized, scoring_rubric),
    }
    save_json(output_dir / "system-extracted" / f"{paper_id}.json", extracted_payload)

    result = build_result(paper_id, image_path, extracted_payload, standard_answers, scoring_rubric)
    save_json(output_dir / "system-reports" / f"{paper_id}.json", result)
    return result


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    template_config = load_template_config(args.template_config)
    grader_config = load_grader_config(args.grader_config)
    standard_answers = load_yaml(args.standard_answers.resolve())
    scoring_rubric = load_yaml(args.scoring_rubric.resolve())
    workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "system-extracted").mkdir(parents=True, exist_ok=True)
    (output_dir / "system-reports").mkdir(parents=True, exist_ok=True)

    selected_ids = resolve_selected_ids(args)
    image_index = index_image_files(args.input_dir.resolve())
    client, model = build_openai_client(grader_config)
    if args.model:
        model = args.model

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    teacher_compare_rows: list[dict[str, Any]] = []

    for paper_id in selected_ids:
        image_path = image_index.get(paper_id)
        if not image_path:
            failures.append({"paper_id": paper_id, "error": "image_not_found"})
            logger.warning("Image not found for %s", paper_id)
            continue
        try:
            result = process_one(client, model, image_path, template_config, standard_answers, scoring_rubric, output_dir)
            results.append(result)
            teacher_truth = load_teacher_truth(workspace, paper_id)
            if teacher_truth:
                teacher_total = teacher_truth.get("total_score")
                system_total = result.get("system_total")
                total_diff = None
                if teacher_total is not None and system_total is not None:
                    total_diff = round(float(system_total) - float(teacher_total), 2)
                teacher_compare_rows.append(
                    {
                        "paper_id": paper_id,
                        "teacher_total": teacher_total,
                        "system_total": system_total,
                        "total_diff": total_diff,
                        "review_required": result.get("review_required"),
                    }
                )
            logger.info("Scored %s total=%s review=%s", paper_id, result["system_total"], result["review_required"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to score %s: %s", paper_id, exc)
            failures.append({"paper_id": paper_id, "error": str(exc)})

    save_json(output_dir / "system_scoring_results.json", {"results": results, "failures": failures})
    save_json(output_dir / "system_scoring_debug_compare.json", {"items": teacher_compare_rows})
    write_debug_split(output_dir, [item["paper_id"] for item in results])
    logger.info("Wrote system scoring results to %s", output_dir / "system_scoring_results.json")


if __name__ == "__main__":
    main()
