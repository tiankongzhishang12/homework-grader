from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from common import ANSWER_CARD_ROOT, extract_json_object, load_grader_config, pil_to_data_url, read_image, save_json

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infer subjective scoring rubric from teacher-scored samples.")
    parser.add_argument("--samples", type=Path, default=None, help="Path to subjective_samples.json.")
    parser.add_argument("--grader-config", type=Path, default=None, help="Optional practicum grader-config.yaml path.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override answer inference output directory.")
    parser.add_argument("--model", type=str, default=None, help="Override model from grader-config.yaml.")
    parser.add_argument("--max-samples-per-bucket", type=int, default=2, help="Max samples per score bucket sent to the model.")
    return parser.parse_args()


def answer_inference_workspace(override: Path | None) -> Path:
    if override:
        return override.resolve()
    return (ANSWER_CARD_ROOT / "workspace" / "answer-inference").resolve()


def build_openai_client(grader_config: dict[str, Any]) -> tuple[OpenAI, str]:
    openai_cfg = grader_config.get("openai", {}) or {}
    api_key = str(openai_cfg.get("api_key", "")).strip()
    base_url = str(openai_cfg.get("base_url", "")).strip() or None
    model = str(openai_cfg.get("model", "")).strip() or "gpt-5.4"
    return OpenAI(api_key=api_key, base_url=base_url), model


def load_samples(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def select_samples(question_payload: dict[str, Any], max_per_bucket: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for bucket in ["full", "high", "mid", "low", "zero"]:
        items = list(question_payload.get("buckets", {}).get(bucket, []) or [])
        selected.extend(items[:max_per_bucket])
    return selected


def build_prompt(qid: str, question_payload: dict[str, Any], samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = {
        "question_id": qid,
        "max_score": question_payload.get("max_score"),
        "score_distribution": question_payload.get("score_distribution", {}),
        "samples": [
            {
                "paper_id": item.get("paper_id"),
                "score": item.get("score"),
                "max_score": item.get("max_score"),
                "bucket": item.get("bucket"),
            }
            for item in samples
        ],
    }
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "你正在根据教师已经评分的主观题样本，归纳该题的候选评分标准。"
                "必须只依据样本图像、教师批注和教师给分归纳，不要凭空补充课程知识。"
                "红色对勾、叉号、+1/+2 和最终得分是教师批注，不是学生答案内容。"
                "请输出严格 JSON，不要输出 Markdown。JSON 结构如下："
                "{"
                '"question_id": string,'
                '"max_score": number,'
                '"inferred_points":[{"description":string,"score":number,"evidence":string,"confidence":number}],'
                '"full_score_features":[string],'
                '"common_missing_points":[string],'
                '"teacher_review_required": boolean,'
                '"notes":[string]'
                "}"
                f"\n样本元数据：{json.dumps(summary, ensure_ascii=False)}"
            ),
        }
    ]
    for item in samples:
        image_path = Path(item.get("crop_paths", {}).get("original", ""))
        if not image_path.exists():
            continue
        image = read_image(image_path)
        content.append(
            {
                "type": "text",
                "text": (
                    f"题 {qid} 样本：paper_id={item.get('paper_id')}, "
                    f"teacher_score={item.get('score')}/{item.get('max_score')}, "
                    f"bucket={item.get('bucket')}"
                ),
            }
        )
        content.append({"type": "image_url", "image_url": {"url": pil_to_data_url(image)}})
    return content


def call_model(client: OpenAI, model: str, qid: str, question_payload: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": build_prompt(qid, question_payload, samples)}],
    )
    text = response.choices[0].message.content or ""
    payload = extract_json_object(text)
    return normalize_rubric_payload(qid, question_payload, payload)


def normalize_rubric_payload(qid: str, question_payload: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    max_score = question_payload.get("max_score")
    payload.setdefault("question_id", qid)
    payload.setdefault("max_score", max_score)
    payload.setdefault("inferred_points", [])
    payload.setdefault("full_score_features", [])
    payload.setdefault("common_missing_points", [])
    payload.setdefault("teacher_review_required", True)
    payload.setdefault("notes", [])
    return payload


def fallback_rubric(qid: str, question_payload: dict[str, Any], reason: str) -> dict[str, Any]:
    max_score = question_payload.get("max_score")
    return {
        "question_id": qid,
        "max_score": max_score,
        "inferred_points": [],
        "full_score_features": [],
        "common_missing_points": [],
        "teacher_review_required": True,
        "notes": [reason],
    }


def write_yaml(output_dir: Path, rubrics: dict[str, Any]) -> Path:
    payload = {
        "exam": {
            "id": "software-requirements-engineering-subjective-rubric-inferred",
            "name": "主观题评分标准候选（样本归纳）",
            "version": 0.1,
            "source": "teacher-scored answer-card samples",
        },
        "subjective_questions": rubrics,
    }
    output_path = output_dir / "inferred_subjective_rubric.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return output_path


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    output_dir = answer_inference_workspace(args.output_dir)
    samples_path = args.samples or (output_dir / "subjective_samples.json")
    output_dir.mkdir(parents=True, exist_ok=True)
    samples_payload = load_samples(samples_path)
    client, model = build_openai_client(load_grader_config(args.grader_config))
    if args.model:
        model = args.model

    rubrics: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    for qid, question_payload in samples_payload.get("questions", {}).items():
        selected = select_samples(question_payload, args.max_samples_per_bucket)
        if not selected:
            rubrics[qid] = fallback_rubric(qid, question_payload, "no_samples")
            continue
        try:
            rubrics[qid] = call_model(client, model, qid, question_payload, selected)
            logger.info("Inferred rubric for question %s", qid)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to infer rubric for question %s: %s", qid, exc)
            failures.append({"question_id": qid, "error": str(exc)})
            rubrics[qid] = fallback_rubric(qid, question_payload, str(exc))

    save_json(output_dir / "subjective_rubric_candidates.json", {"subjective_questions": rubrics, "failures": failures})
    yaml_path = write_yaml(output_dir, rubrics)
    logger.info("Wrote subjective rubric candidates to %s", output_dir / "subjective_rubric_candidates.json")
    logger.info("Wrote inferred subjective rubric to %s", yaml_path)


if __name__ == "__main__":
    main()
