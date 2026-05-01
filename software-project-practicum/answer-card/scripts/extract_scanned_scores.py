from __future__ import annotations

import argparse
import logging
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI
from PIL import Image
from scipy import ndimage

from common import (
    ensure_phase1_dirs,
    extract_json_object,
    iter_image_files,
    load_grader_config,
    load_template_config,
    paper_id_from_path,
    parse_paper_filename,
    phase1_workspace_path,
    pil_to_data_url,
    read_image,
    safe_float,
    save_json,
    scanned_input_path,
)

logger = logging.getLogger(__name__)

SECTION_REGION_IDS = ["single_choice_score", "true_false_score", "fill_blank_score"]
QUESTION_REGION_IDS = ["q26_score", "q27_score", "q28_score", "q29_score", "q30_score", "q31_score", "q32_score", "q33_score"]
MODEL_RETRY_COUNT = 2
GROUP_DEFINITIONS = {
    "left_panel": {
        "bbox_ratio": [0.0, 0.0, 0.5, 1.0],
        "fields": [
            "total_score",
            "single_choice_score",
            "true_false_score",
            "fill_blank_score",
            "q26_score",
            "q30_score",
            "q31_score",
        ],
        "label": "左侧两页区域，包含总分、客观题得分、第26题、第30题、第31题评分信息",
    },
    "right_panel": {
        "bbox_ratio": [0.5, 0.0, 1.0, 1.0],
        "fields": [
            "q27_score",
            "q28_score",
            "q29_score",
            "q32_score",
            "q33_score",
        ],
        "label": "右侧两页区域，包含第27题、第28题、第29题、第32题、第33题评分信息",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract teacher scores from graded answer-card scans.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--grader-config", type=Path, default=None, help="Optional practicum grader-config.yaml path.")
    parser.add_argument("--input-dir", type=Path, default=None, help="Override the scanned answer-card input directory.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument("--split-file", type=Path, default=None, help="Only process paper ids listed in this file.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N images.")
    parser.add_argument("--skip-export", action="store_true", help="Skip automatic Excel export after extraction.")
    return parser.parse_args()


def read_id_list(path: Path) -> set[str]:
    ids: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            text = line.strip().lstrip("\ufeff")
            if text:
                ids.add(text)
    return ids


def build_openai_client(grader_config: dict[str, Any]) -> tuple[OpenAI, str]:
    openai_cfg = grader_config.get("openai", {}) or {}
    api_key = str(openai_cfg.get("api_key", "")).strip()
    base_url = str(openai_cfg.get("base_url", "")).strip() or None
    model = str(openai_cfg.get("model", "")).strip() or "gpt-5.4"
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def estimate_answer_card_bounds(image: Image.Image, template_cfg: dict[str, Any]) -> dict[str, Any]:
    gray = np.asarray(image.convert("L"))
    width, height = image.size
    threshold = int(template_cfg.get("dark_threshold", 72) or 72)
    edge_ratio = float(template_cfg.get("edge_search_ratio", 0.16) or 0.16)
    border_padding = int(template_cfg.get("border_padding", 18) or 18)
    edge_x = max(50, int(width * edge_ratio))
    edge_y = max(50, int(height * edge_ratio))
    dark_mask = gray <= threshold
    labels, count = ndimage.label(dark_mask)
    objects = ndimage.find_objects(labels)
    corners: dict[str, tuple[float, float]] = {}

    def region_score(cx: float, cy: float, target_x: float, target_y: float) -> float:
        return abs(cx - target_x) + abs(cy - target_y)

    candidates: dict[str, list[tuple[float, tuple[float, float], tuple[int, int, int, int]]]] = defaultdict(list)
    for label_index, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        y0, y1 = slc[0].start, slc[0].stop
        x0, x1 = slc[1].start, slc[1].stop
        box_w = x1 - x0
        box_h = y1 - y0
        area = box_w * box_h
        if area < 80:
            continue
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        near_left = cx <= edge_x
        near_right = cx >= width - edge_x
        near_top = cy <= edge_y
        near_bottom = cy >= height - edge_y
        if near_left and near_top:
            candidates["top_left"].append((region_score(cx, cy, 0, 0), (cx, cy), (x0, y0, x1, y1)))
        if near_right and near_top:
            candidates["top_right"].append((region_score(cx, cy, width, 0), (cx, cy), (x0, y0, x1, y1)))
        if near_left and near_bottom:
            candidates["bottom_left"].append((region_score(cx, cy, 0, height), (cx, cy), (x0, y0, x1, y1)))
        if near_right and near_bottom:
            candidates["bottom_right"].append((region_score(cx, cy, width, height), (cx, cy), (x0, y0, x1, y1)))

    for key, items in candidates.items():
        if items:
            items.sort(key=lambda item: item[0])
            corners[key] = items[0][1]

    if len(corners) == 4:
        xs = [value[0] for value in corners.values()]
        ys = [value[1] for value in corners.values()]
        left = max(0, int(min(xs) - border_padding))
        top = max(0, int(min(ys) - border_padding))
        right = min(width, int(max(xs) + border_padding))
        bottom = min(height, int(max(ys) + border_padding))
        return {
            "bbox": [left, top, right, bottom],
            "corners_found": True,
            "corners": {key: [round(value[0], 1), round(value[1], 1)] for key, value in corners.items()},
        }

    return {
        "bbox": [0, 0, width, height],
        "corners_found": False,
        "corners": {key: [round(value[0], 1), round(value[1], 1)] for key, value in corners.items()},
    }


def normalize_scan(image: Image.Image, template_cfg: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    bounds = estimate_answer_card_bounds(image, template_cfg)
    left, top, right, bottom = bounds["bbox"]
    cropped = image.crop((left, top, right, bottom))
    target_width = int(template_cfg.get("width", image.width))
    target_height = int(template_cfg.get("height", image.height))
    normalized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
    debug = {
        "source_size": [image.width, image.height],
        "normalized_size": [normalized.width, normalized.height],
        "crop_bbox": bounds["bbox"],
        "corners_found": bounds["corners_found"],
        "corners": bounds["corners"],
    }
    return normalized, debug


def create_red_mask(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"))
    red_mask = (
        (rgb[:, :, 0] >= 150)
        & (rgb[:, :, 0] - rgb[:, :, 1] >= 35)
        & (rgb[:, :, 0] - rgb[:, :, 2] >= 35)
    )
    output = np.full_like(rgb, 255)
    output[red_mask] = [220, 0, 0]
    return Image.fromarray(output)


def crop_regions(image: Image.Image, template_config: dict[str, Any]) -> dict[str, dict[str, Image.Image]]:
    regions = template_config.get("regions", {}) or {}
    payload: dict[str, dict[str, Image.Image]] = {}
    red_mask = create_red_mask(image)
    for region_id, region in regions.items():
        x = int(region.get("x", 0))
        y = int(region.get("y", 0))
        w = int(region.get("w", 0))
        h = int(region.get("h", 0))
        box = (x, y, x + w, y + h)
        payload[region_id] = {
            "original": image.crop(box),
            "red_mask": red_mask.crop(box),
        }
    return payload


def save_region_crops(crops_dir: Path, paper_id: str, region_images: dict[str, dict[str, Image.Image]]) -> None:
    paper_dir = crops_dir / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    for region_id, variants in region_images.items():
        for variant, image in variants.items():
            image.save(paper_dir / f"{region_id}-{variant}.png")


def build_single_field_prompt(field_name: str, label: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "你在读取一张已经批改完成的答题卡局部截图。"
                f"当前只需要提取字段 `{field_name}`，区域说明：{label}。"
                "只识别教师红笔批注中的分数，不要读取学生黑色手写正文。"
                "如果区域同时出现“得分”和“满分”，只返回得分。"
                "如果只有对勾、叉号、+2 之类批注，但看不到该字段对应的最终分数，请返回 null。"
                "只返回一个 JSON 对象，格式为："
                f'{{"{field_name}": number|null, "note": string}}'
            ),
        },
        {"type": "text", "text": "原图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:single:original"}},
        {"type": "text", "text": "红色批注增强图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:single:red_mask"}},
    ]


def build_group_prompt(group_label: str, fields: list[str]) -> list[dict[str, Any]]:
    json_fields = ", ".join([f'"{field}": number|null' for field in fields] + ['"notes": [string]'])
    return [
        {
            "type": "text",
            "text": (
                "你在读取一张已经批改完成的答题卡较大区域截图。"
                f"当前区域说明：{group_label}。"
                "请只提取该区域内教师红笔最终写出的分数。"
                "不要把红色对勾、叉号、局部 +2 批注误当成题目最终得分。"
                "如果某字段没有看到可靠的最终分数，就返回 null。"
                "只返回一个 JSON 对象，字段固定如下："
                "{"
                + json_fields
                + "}"
            ),
        },
        {"type": "text", "text": "原图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:single:original"}},
        {"type": "text", "text": "红色批注增强图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:single:red_mask"}},
    ]


def resolve_prompt_images(
    content_template: list[dict[str, Any]],
    region_images: dict[str, dict[str, Image.Image]],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in content_template:
        if item.get("type") != "image_url":
            resolved.append(item)
            continue
        raw_url = str(item.get("image_url", {}).get("url", ""))
        match = re.match(r"^__IMAGE__:(.+?):(original|red_mask)$", raw_url)
        if not match:
            resolved.append(item)
            continue
        region_id = match.group(1)
        variant = match.group(2)
        image = region_images[region_id][variant]
        resolved.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": pil_to_data_url(image),
                },
            }
        )
    return resolved


def call_model_for_scores(
    client: OpenAI,
    model: str,
    content_template: list[dict[str, Any]],
    region_images: dict[str, dict[str, Image.Image]],
) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(MODEL_RETRY_COUNT):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": resolve_prompt_images(content_template, region_images),
                    }
                ],
            )
            text = response.choices[0].message.content or ""
            return extract_json_object(text)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if last_error is None:
        raise RuntimeError("model returned no response")
    raise last_error


def crop_group_images(image: Image.Image) -> dict[str, dict[str, Image.Image]]:
    width, height = image.size
    red_mask = create_red_mask(image)
    payload: dict[str, dict[str, Image.Image]] = {}
    for group_id, definition in GROUP_DEFINITIONS.items():
        x0_ratio, y0_ratio, x1_ratio, y1_ratio = definition["bbox_ratio"]
        box = (
            int(width * x0_ratio),
            int(height * y0_ratio),
            int(width * x1_ratio),
            int(height * y1_ratio),
        )
        payload[group_id] = {
            "original": image.crop(box),
            "red_mask": red_mask.crop(box),
        }
    return payload


def merge_score_payload(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if key == "notes":
            merged.setdefault("notes", [])
            extra_notes = value if isinstance(value, list) else [value]
            merged["notes"].extend(str(item).strip() for item in extra_notes if str(item).strip())
            continue
        if merged.get(key) is None and value is not None:
            merged[key] = value
    return merged


def call_group_and_region_scores(
    client: OpenAI,
    model: str,
    normalized_image: Image.Image,
    region_images: dict[str, dict[str, Image.Image]],
    template_config: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "total_score": None,
        "single_choice_score": None,
        "true_false_score": None,
        "fill_blank_score": None,
        "q26_score": None,
        "q27_score": None,
        "q28_score": None,
        "q29_score": None,
        "q30_score": None,
        "q31_score": None,
        "q32_score": None,
        "q33_score": None,
        "notes": [],
    }

    group_images = crop_group_images(normalized_image)
    for group_id, definition in GROUP_DEFINITIONS.items():
        prompt = build_group_prompt(str(definition["label"]), list(definition["fields"]))
        group_payload = call_model_for_scores(client, model, prompt, {"single": group_images[group_id]})
        merged = merge_score_payload(merged, group_payload)

    regions = template_config.get("regions", {}) or {}
    for field_name in [key for key, value in merged.items() if key != "notes" and value is None]:
        if field_name not in regions:
            continue
        label = str(regions[field_name].get("prompt_label", field_name))
        prompt = build_single_field_prompt(field_name, label)
        field_payload = call_model_for_scores(client, model, prompt, {"single": region_images[field_name]})
        merged = merge_score_payload(merged, field_payload)

    return merged


def normalize_score_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ["total_score", "single_choice_score", "true_false_score", "fill_blank_score", *QUESTION_REGION_IDS]:
        result[key] = safe_float(raw_payload.get(key))
    notes = raw_payload.get("notes", [])
    if isinstance(notes, list):
        result["notes"] = [str(item).strip() for item in notes if str(item).strip()]
    else:
        note_text = str(notes).strip()
        result["notes"] = [note_text] if note_text else []
    return result


def build_validation(score_payload: dict[str, Any], template_config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    limits = template_config.get("score_limits", {}) or {}
    issues: list[str] = []
    checks: dict[str, Any] = {}
    missing_score_fields: list[str] = []
    for key, limit in limits.items():
        lookup_key = key if key == "total_score" else f"{key}_score" if key in {"single_choice", "true_false", "fill_blank"} else f"{key}_score"
        value = score_payload.get(lookup_key)
        if value is None:
            checks[f"{lookup_key}_present"] = False
            missing_score_fields.append(lookup_key)
            continue
        checks[f"{lookup_key}_present"] = True
        if value < 0 or value > float(limit):
            issues.append(f"{lookup_key}_out_of_range")

    short_parts = [score_payload.get("q26_score"), score_payload.get("q27_score"), score_payload.get("q28_score"), score_payload.get("q29_score")]
    comprehensive_parts = [score_payload.get("q30_score"), score_payload.get("q31_score"), score_payload.get("q32_score"), score_payload.get("q33_score")]
    objective_parts = [score_payload.get("single_choice_score"), score_payload.get("true_false_score"), score_payload.get("fill_blank_score")]
    short_sum = sum(value for value in short_parts if value is not None) if all(value is not None for value in short_parts) else None
    comprehensive_sum = (
        sum(value for value in comprehensive_parts if value is not None)
        if all(value is not None for value in comprehensive_parts)
        else None
    )
    objective_sum = sum(value for value in objective_parts if value is not None) if all(value is not None for value in objective_parts) else None
    complete_total = (
        objective_sum is not None
        and short_sum is not None
        and comprehensive_sum is not None
    )
    computed_total = objective_sum + short_sum + comprehensive_sum if complete_total else None
    total_score = score_payload.get("total_score")
    if computed_total is not None and total_score is not None and not math.isclose(computed_total, total_score, abs_tol=0.5):
        issues.append("section_sum_not_match_total")
    if total_score is None:
        issues.append("total_score_missing")
    if missing_score_fields:
        issues.append("score_fields_missing")

    checks["computed_short_answer_sum"] = short_sum
    checks["computed_comprehensive_sum"] = comprehensive_sum
    checks["computed_total"] = computed_total
    checks["missing_score_fields"] = missing_score_fields
    checks["sum_matches_total"] = bool(
        computed_total is not None and total_score is not None and math.isclose(computed_total, total_score, abs_tol=0.5)
    )
    checks["issues"] = issues
    return checks, bool(issues)


def build_result_payload(
    image_path: Path,
    model_scores: dict[str, Any],
    validation: dict[str, Any],
    normalize_debug: dict[str, Any],
) -> dict[str, Any]:
    student_number, student_name = parse_paper_filename(image_path)
    paper_id = paper_id_from_path(image_path)
    question_scores = {
        "26": model_scores.get("q26_score"),
        "27": model_scores.get("q27_score"),
        "28": model_scores.get("q28_score"),
        "29": model_scores.get("q29_score"),
        "30": model_scores.get("q30_score"),
        "31": model_scores.get("q31_score"),
        "32": model_scores.get("q32_score"),
        "33": model_scores.get("q33_score"),
    }
    section_scores = {
        "single_choice": model_scores.get("single_choice_score"),
        "true_false": model_scores.get("true_false_score"),
        "fill_blank": model_scores.get("fill_blank_score"),
        "short_answer": validation.get("computed_short_answer_sum"),
        "comprehensive": validation.get("computed_comprehensive_sum"),
    }
    notes = list(model_scores.get("notes", []) or [])
    notes.extend(validation.get("issues", []))
    confidence_base = 0.98
    if validation.get("issues"):
        confidence_base = 0.72
    if model_scores.get("total_score") is None:
        confidence_base = min(confidence_base, 0.55)
    if validation.get("missing_score_fields"):
        confidence_base = min(confidence_base, 0.6)

    return {
        "paper_id": paper_id,
        "student_number": student_number,
        "student_name": student_name,
        "source_image": str(image_path),
        "total_score": model_scores.get("total_score"),
        "section_scores": section_scores,
        "question_scores": question_scores,
        "checks": validation,
        "notes": notes,
        "needs_review": bool(validation.get("issues")),
        "confidence": {
            "overall": confidence_base,
            "total_score": 0.98 if model_scores.get("total_score") is not None else 0.0,
            "question_scores": 0.9 if all(value is not None for value in question_scores.values()) else 0.62,
        },
        "normalization": normalize_debug,
    }


def process_one_image(
    image_path: Path,
    template_config: dict[str, Any],
    client: OpenAI,
    model: str,
    phase1_dirs: dict[str, Path],
) -> dict[str, Any]:
    paper_id = paper_id_from_path(image_path)
    image = read_image(image_path)
    normalized, normalize_debug = normalize_scan(image, template_config.get("template", {}) or {})
    normalized_output = phase1_dirs["normalized"] / f"{paper_id}.png"
    normalized.save(normalized_output)
    region_images = crop_regions(normalized, template_config)
    save_region_crops(phase1_dirs["crops"], paper_id, region_images)
    raw_payload = call_group_and_region_scores(client, model, normalized, region_images, template_config)
    model_scores = normalize_score_payload(raw_payload)
    validation, _ = build_validation(model_scores, template_config)
    result = build_result_payload(image_path, model_scores, validation, normalize_debug)
    save_json(phase1_dirs["parsed"] / f"{paper_id}.json", result)
    logger.info("Processed %s review=%s total=%s", paper_id, result["needs_review"], result["total_score"])
    return result


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    template_config = load_template_config(args.template_config)
    grader_config = load_grader_config(args.grader_config)
    input_dir = args.input_dir.resolve() if args.input_dir else scanned_input_path(template_config)
    workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    phase1_dirs = ensure_phase1_dirs(workspace)
    client, model = build_openai_client(grader_config)

    image_files = iter_image_files(input_dir)
    if args.split_file:
        allowed_ids = read_id_list(args.split_file.resolve())
        image_files = [path for path in image_files if paper_id_from_path(path) in allowed_ids]
    if args.limit:
        image_files = image_files[: args.limit]
    if not image_files:
        logger.warning("No scanned answer-card images found in %s", input_dir)
        return

    results: list[dict[str, Any]] = []
    for image_path in image_files:
        try:
            results.append(process_one_image(image_path, template_config, client, model, phase1_dirs))
        except Exception as exc:  # noqa: BLE001
            paper_id = paper_id_from_path(image_path)
            failure_payload = {
                "paper_id": paper_id,
                "student_number": parse_paper_filename(image_path)[0],
                "student_name": parse_paper_filename(image_path)[1],
                "source_image": str(image_path),
                "error": str(exc),
                "needs_review": True,
                "total_score": None,
                "section_scores": {},
                "question_scores": {},
                "checks": {"issues": ["pipeline_failed"]},
                "notes": [str(exc)],
                "confidence": {"overall": 0.0},
            }
            save_json(phase1_dirs["parsed"] / f"{paper_id}.json", failure_payload)
            results.append(failure_payload)
            logger.exception("Failed to process %s", image_path)

    review_list = [item for item in results if item.get("needs_review")]
    save_json(phase1_dirs["review"] / "review-list.json", {"count": len(review_list), "items": review_list})

    if not args.skip_export:
        from export_scores_excel import export_phase1_results

        export_phase1_results(workspace)


if __name__ == "__main__":
    main()
