from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image

from common import (
    ANSWER_CARD_ROOT,
    ensure_phase1_dirs,
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

OBJECTIVE_FIELDS = {
    "single_choice": [str(index) for index in range(1, 11)],
    "true_false": [str(index) for index in range(11, 21)],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infer objective standard answers from teacher-marked answer cards.")
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


def answer_inference_workspace(default_workspace: Path, override: Path | None) -> Path:
    if override:
        return override.resolve()
    return (ANSWER_CARD_ROOT / "workspace" / "answer-inference").resolve()


def ensure_inference_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "root": output_dir,
        "crops": output_dir / "crops",
        "reports": output_dir / "reports",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def crop_objective_area(normalized: Image.Image) -> dict[str, Image.Image]:
    width, height = normalized.size
    red_mask = create_red_mask(normalized)
    # The objective section is on the upper-left half of the 4-page scan.
    # Keep a generous crop so teacher-provided blue/red answer marks remain visible.
    box = (
        int(width * 0.015),
        int(height * 0.115),
        int(width * 0.495),
        int(height * 0.315),
    )
    return {
        "original": normalized.crop(box),
        "red_mask": red_mask.crop(box),
    }


def save_objective_crop(crops_dir: Path, paper_id: str, crops: dict[str, Image.Image]) -> None:
    paper_dir = crops_dir / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    for name, image in crops.items():
        image.save(paper_dir / f"objective-{name}.png")


def build_prompt() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "你在读取一张已经批改完成的答题卡客观题区域。"
                "目标是反推出标准答案，不是读取学生作答。"
                "请优先读取教师批改时标出的正确答案。"
                "客观题区域中，题号附近或选项右侧的蓝色大写 A/B/C/D/T/F 通常就是教师标出的标准答案，必须优先提取。"
                "红色总得分、满分、对勾、叉号不是标准答案；黑色涂卡块通常是学生作答，不能作为标准答案。"
                "如果某题没有可靠教师标注，则返回 null，不要猜。"
                "单选题只允许 A/B/C/D/null；判断题只允许 T/F/null。"
                "请只返回 JSON 对象，格式如下："
                "{"
                '"single_choice":{"1":"A|null","2":"A|null","3":"A|null","4":"A|null","5":"A|null","6":"A|null","7":"A|null","8":"A|null","9":"A|null","10":"A|null"},'
                '"true_false":{"11":"T|null","12":"T|null","13":"T|null","14":"T|null","15":"T|null","16":"T|null","17":"T|null","18":"T|null","19":"T|null","20":"T|null"},'
                '"notes":[string]'
                "}"
            ),
        },
        {"type": "text", "text": "客观题区域原图"},
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


def normalize_answer_value(value: Any, allowed: set[str]) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"", "NULL", "NONE", "UNKNOWN", "不确定"}:
        return None
    if text in allowed:
        return text
    return None


def normalize_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    single_raw = payload.get("single_choice", {}) or {}
    tf_raw = payload.get("true_false", {}) or {}
    normalized = {
        "single_choice": {
            qid: normalize_answer_value(single_raw.get(qid), {"A", "B", "C", "D"})
            for qid in OBJECTIVE_FIELDS["single_choice"]
        },
        "true_false": {
            qid: normalize_answer_value(tf_raw.get(qid), {"T", "F"})
            for qid in OBJECTIVE_FIELDS["true_false"]
        },
        "notes": [],
    }
    notes = payload.get("notes", []) or []
    if isinstance(notes, list):
        normalized["notes"] = [str(item).strip() for item in notes if str(item).strip()]
    else:
        note_text = str(notes).strip()
        normalized["notes"] = [note_text] if note_text else []
    return normalized


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
    crops = crop_objective_area(normalized)
    save_objective_crop(dirs["crops"], paper_id, crops)
    answers = call_model(client, model, crops)
    payload = {
        "paper_id": paper_id,
        "source_image": str(image_path),
        "answers": answers,
        "normalization": normalize_debug,
    }
    save_json(dirs["reports"] / f"{paper_id}.json", payload)
    logger.info("Processed objective inference for %s", paper_id)
    return payload


def aggregate_candidates(results: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {
        "single_choice": {},
        "true_false": {},
        "metadata": {
            "sample_count": len(results),
        },
    }
    for section, qids in OBJECTIVE_FIELDS.items():
        for qid in qids:
            counter: Counter[str] = Counter()
            support_papers: dict[str, list[str]] = defaultdict(list)
            for result in results:
                answer = result.get("answers", {}).get(section, {}).get(qid)
                if not answer:
                    continue
                counter[answer] += 1
                support_papers[answer].append(str(result.get("paper_id", "")))

            total_votes = sum(counter.values())
            if not total_votes:
                aggregate[section][qid] = {
                    "candidate": None,
                    "confidence": 0.0,
                    "votes": {},
                    "support_count": 0,
                    "review_required": True,
                    "review_reason": "no_reliable_votes",
                }
                continue

            candidate, count = counter.most_common(1)[0]
            confidence = round(count / total_votes, 4)
            aggregate[section][qid] = {
                "candidate": candidate,
                "confidence": confidence,
                "votes": dict(counter),
                "support_count": total_votes,
                "support_papers": support_papers[candidate][:20],
                "review_required": confidence < 0.85 or len(counter) > 1,
                "review_reason": "conflicting_votes" if len(counter) > 1 else "",
            }
    return aggregate


def write_inferred_standard_answers(output_dir: Path, aggregate: dict[str, Any]) -> Path:
    import yaml

    single_answers = {
        qid: item.get("candidate")
        for qid, item in aggregate.get("single_choice", {}).items()
    }
    tf_answers = {
        qid: item.get("candidate")
        for qid, item in aggregate.get("true_false", {}).items()
    }
    review_required = [
        f"single_choice.{qid}"
        for qid, item in aggregate.get("single_choice", {}).items()
        if item.get("review_required")
    ]
    review_required.extend(
        f"true_false.{qid}"
        for qid, item in aggregate.get("true_false", {}).items()
        if item.get("review_required")
    )
    payload = {
        "exam": {
            "id": "software-requirements-engineering-objective-inferred",
            "name": "客观题反推标准答案候选",
            "version": 0.1,
            "source": "teacher-marked scanned answer cards",
        },
        "single_choice": {
            "answers": single_answers,
            "confidence": {
                qid: item.get("confidence")
                for qid, item in aggregate.get("single_choice", {}).items()
            },
        },
        "true_false": {
            "answers": tf_answers,
            "confidence": {
                qid: item.get("confidence")
                for qid, item in aggregate.get("true_false", {}).items()
            },
        },
        "review_required": review_required,
    }
    output_path = output_dir / "inferred_standard_answers.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return output_path


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    template_config = load_template_config(args.template_config)
    grader_config = load_grader_config(args.grader_config)
    input_dir = args.input_dir.resolve() if args.input_dir else scanned_input_path(template_config)
    phase1_workspace = args.workspace.resolve() if args.workspace else phase1_workspace_path(template_config)
    ensure_phase1_dirs(phase1_workspace)
    output_dir = answer_inference_workspace(phase1_workspace, args.output_dir)
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
            logger.exception("Failed to infer objective answers from %s: %s", image_path, exc)
            failures.append(
                {
                    "paper_id": paper_id_from_path(image_path),
                    "source_image": str(image_path),
                    "error": str(exc),
                }
            )

    aggregate = aggregate_candidates(results)
    aggregate["metadata"]["failure_count"] = len(failures)
    save_json(output_dir / "objective_candidates.json", aggregate)
    save_json(output_dir / "objective_failures.json", {"count": len(failures), "items": failures})
    inferred_path = write_inferred_standard_answers(output_dir, aggregate)
    logger.info("Wrote objective candidates to %s", output_dir / "objective_candidates.json")
    logger.info("Wrote objective failures to %s", output_dir / "objective_failures.json")
    logger.info("Wrote inferred standard answers to %s", inferred_path)


if __name__ == "__main__":
    main()
