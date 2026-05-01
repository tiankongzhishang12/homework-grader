from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter, defaultdict
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
    paper_id_from_path,
    phase1_workspace_path,
    pil_to_data_url,
    read_image,
    save_json,
    scanned_input_path,
)
from extract_scanned_scores import create_red_mask, normalize_scan

logger = logging.getLogger(__name__)

FILL_QIDS = [str(index) for index in range(21, 26)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infer fill-blank answer candidates from teacher-marked cards.")
    parser.add_argument("--template-config", type=Path, default=None, help="Optional answer-card template yaml path.")
    parser.add_argument("--grader-config", type=Path, default=None, help="Optional practicum grader-config.yaml path.")
    parser.add_argument("--input-dir", type=Path, default=None, help="Override scanned answer-card input directory.")
    parser.add_argument("--workspace", type=Path, default=None, help="Override phase1 workspace directory.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override answer inference output directory.")
    parser.add_argument("--model", type=str, default=None, help="Override the model from grader-config.yaml.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N images.")
    return parser.parse_args()


def build_openai_client(grader_config: dict[str, Any]) -> tuple[OpenAI, str]:
    openai_cfg = grader_config.get("openai", {}) or {}
    api_key = str(openai_cfg.get("api_key", "")).strip()
    base_url = str(openai_cfg.get("base_url", "")).strip() or None
    model = str(openai_cfg.get("model", "")).strip() or "gpt-5.4"
    return OpenAI(api_key=api_key, base_url=base_url), model


def answer_inference_workspace(override: Path | None) -> Path:
    if override:
        return override.resolve()
    return (ANSWER_CARD_ROOT / "workspace" / "answer-inference").resolve()


def ensure_inference_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "root": output_dir,
        "crops": output_dir / "crops",
        "fill_reports": output_dir / "fill-reports",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def crop_fill_blank_area(normalized: Image.Image) -> dict[str, Image.Image]:
    width, height = normalized.size
    red_mask = create_red_mask(normalized)
    # Fill blanks are on the left page, below the true/false area and above question 26.
    box = (
        int(width * 0.01),
        int(height * 0.235),
        int(width * 0.50),
        int(height * 0.335),
    )
    return {
        "original": normalized.crop(box),
        "red_mask": red_mask.crop(box),
    }


def save_fill_crop(crops_dir: Path, paper_id: str, crops: dict[str, Image.Image]) -> None:
    paper_dir = crops_dir / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    for name, image in crops.items():
        image.save(paper_dir / f"fill_blank-{name}.png")


def build_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "你在读取一张已批改答题卡的填空题区域，题号为21-25。"
                "请提取每一题学生黑色手写答案，并判断老师是否认可该空。"
                "老师认可的证据包括：该题旁边有红色“2分”、红色对勾，或整道填空题区域显示该空得满分。"
                "老师不认可的证据包括：红色叉号、该题未给分、明显批改否定。"
                "如果无法可靠判断认可状态，accepted 返回 null。"
                "不要把红色教师姓名、评分文字、满分文字当成学生答案。"
                "只返回 JSON 对象，格式如下："
                "{"
                '"answers":{'
                '"21":{"text":string|null,"accepted":true|false|null,"score":number|null},'
                '"22":{"text":string|null,"accepted":true|false|null,"score":number|null},'
                '"23":{"text":string|null,"accepted":true|false|null,"score":number|null},'
                '"24":{"text":string|null,"accepted":true|false|null,"score":number|null},'
                '"25":{"text":string|null,"accepted":true|false|null,"score":number|null}'
                "},"
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "text", "text": "填空题区域原图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:original"}},
        {"type": "text", "text": "红色批注增强图"},
        {"type": "image_url", "image_url": {"url": "__IMAGE__:red_mask"}},
    ]


def resolve_prompt_images(prompt: list[dict[str, Any]], crops: dict[str, Image.Image]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in prompt:
        if item.get("type") != "image_url":
            resolved.append(item)
            continue
        url = str(item.get("image_url", {}).get("url", ""))
        if url == "__IMAGE__:original":
            resolved.append({"type": "image_url", "image_url": {"url": pil_to_data_url(crops["original"])}})
        elif url == "__IMAGE__:red_mask":
            resolved.append({"type": "image_url", "image_url": {"url": pil_to_data_url(crops["red_mask"])}})
        else:
            resolved.append(item)
    return resolved


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    value = re.sub(r"\s+", "", value)
    value = value.replace("（", "(").replace("）", ")")
    value = value.strip("，。,.、；;：: ")
    return value


def normalize_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_answers = payload.get("answers", {}) or {}
    answers: dict[str, dict[str, Any]] = {}
    for qid in FILL_QIDS:
        item = raw_answers.get(qid, {}) or {}
        accepted = item.get("accepted")
        if isinstance(accepted, str):
            lowered = accepted.strip().lower()
            if lowered in {"true", "yes", "y", "1", "accepted"}:
                accepted = True
            elif lowered in {"false", "no", "n", "0", "rejected"}:
                accepted = False
            else:
                accepted = None
        if accepted not in {True, False, None}:
            accepted = None
        score = item.get("score")
        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        answers[qid] = {
            "text": normalize_text(item.get("text")) or None,
            "accepted": accepted,
            "score": score,
        }
    notes = payload.get("notes", []) or []
    if isinstance(notes, list):
        note_list = [str(item).strip() for item in notes if str(item).strip()]
    else:
        note_text = str(notes).strip()
        note_list = [note_text] if note_text else []
    return {"answers": answers, "notes": note_list}


def call_model(client: OpenAI, model: str, crops: dict[str, Image.Image]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": resolve_prompt_images(build_prompt(), crops),
            }
        ],
    )
    text = response.choices[0].message.content or ""
    return normalize_model_payload(extract_json_object(text))


def process_one(
    image_path: Path,
    template_config: dict[str, Any],
    client: OpenAI,
    model: str,
    dirs: dict[str, Path],
) -> dict[str, Any]:
    paper_id = paper_id_from_path(image_path)
    image = read_image(image_path)
    normalized, normalize_debug = normalize_scan(image, template_config.get("template", {}) or {})
    crops = crop_fill_blank_area(normalized)
    save_fill_crop(dirs["crops"], paper_id, crops)
    extracted = call_model(client, model, crops)
    payload = {
        "paper_id": paper_id,
        "source_image": str(image_path),
        "fill_blank": extracted,
        "normalization": normalize_debug,
    }
    save_json(dirs["fill_reports"] / f"{paper_id}.json", payload)
    logger.info("Processed fill-blank inference for %s", paper_id)
    return payload


def aggregate_candidates(results: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {
        "fill_blank": {},
        "metadata": {
            "sample_count": len(results),
        },
    }
    for qid in FILL_QIDS:
        accepted_counter: Counter[str] = Counter()
        rejected_counter: Counter[str] = Counter()
        unknown_counter: Counter[str] = Counter()
        support_papers: dict[str, list[str]] = defaultdict(list)
        for result in results:
            item = result.get("fill_blank", {}).get("answers", {}).get(qid, {}) or {}
            text = normalize_text(item.get("text"))
            if not text:
                continue
            accepted = item.get("accepted")
            if accepted is True or item.get("score") == 2:
                accepted_counter[text] += 1
                support_papers[text].append(str(result.get("paper_id", "")))
            elif accepted is False:
                rejected_counter[text] += 1
            else:
                unknown_counter[text] += 1

        total_accepted = sum(accepted_counter.values())
        canonical = accepted_counter.most_common(1)[0][0] if accepted_counter else None
        aliases = [
            text
            for text, count in accepted_counter.most_common()
            if text != canonical and count >= 2
        ]
        aggregate["fill_blank"][qid] = {
            "canonical_candidate": canonical,
            "aliases": aliases,
            "accepted_votes": dict(accepted_counter),
            "wrong_examples": dict(rejected_counter),
            "unknown_examples": dict(unknown_counter),
            "support_count": total_accepted,
            "support_papers": support_papers.get(canonical or "", [])[:20],
            "confidence": round((accepted_counter[canonical] / total_accepted), 4) if canonical and total_accepted else 0.0,
            "review_required": total_accepted == 0 or len(accepted_counter) > 1,
            "review_reason": "no_accepted_votes" if total_accepted == 0 else ("multiple_accepted_forms" if len(accepted_counter) > 1 else ""),
        }
    return aggregate


def write_inferred_fill_answers(output_dir: Path, aggregate: dict[str, Any]) -> Path:
    import yaml

    answers: dict[str, Any] = {}
    review_required: list[str] = []
    for qid, item in aggregate.get("fill_blank", {}).items():
        answers[qid] = {
            "canonical": item.get("canonical_candidate"),
            "aliases": item.get("aliases", []),
            "confidence": item.get("confidence", 0.0),
        }
        if item.get("review_required"):
            review_required.append(qid)
    payload = {
        "exam": {
            "id": "software-requirements-engineering-fill-blank-inferred",
            "name": "填空题反推候选答案",
            "version": 0.1,
            "source": "teacher-marked scanned answer cards",
        },
        "fill_blank": {
            "answers": answers,
        },
        "review_required": review_required,
    }
    output_path = output_dir / "inferred_fill_blank_answers.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return output_path


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    template_config = load_template_config(args.template_config)
    grader_config = load_grader_config(args.grader_config)
    input_dir = args.input_dir.resolve() if args.input_dir else scanned_input_path(template_config)
    _ = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    output_dir = answer_inference_workspace(args.output_dir)
    dirs = ensure_inference_dirs(output_dir)
    client, model = build_openai_client(grader_config)
    if args.model:
        model = args.model

    image_files = iter_image_files(input_dir)
    if args.limit:
        image_files = image_files[: args.limit]

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for image_path in image_files:
        try:
            results.append(process_one(image_path, template_config, client, model, dirs))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to infer fill-blank answers from %s: %s", image_path, exc)
            failures.append(
                {
                    "paper_id": paper_id_from_path(image_path),
                    "source_image": str(image_path),
                    "error": str(exc),
                }
            )

    aggregate = aggregate_candidates(results)
    aggregate["metadata"]["failure_count"] = len(failures)
    save_json(output_dir / "fill_blank_candidates.json", aggregate)
    save_json(output_dir / "fill_blank_failures.json", {"count": len(failures), "items": failures})
    inferred_path = write_inferred_fill_answers(output_dir, aggregate)
    logger.info("Wrote fill-blank candidates to %s", output_dir / "fill_blank_candidates.json")
    logger.info("Wrote fill-blank failures to %s", output_dir / "fill_blank_failures.json")
    logger.info("Wrote inferred fill-blank answers to %s", inferred_path)


if __name__ == "__main__":
    main()
