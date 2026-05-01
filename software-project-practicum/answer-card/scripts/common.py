from __future__ import annotations

import base64
import io
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
ANSWER_CARD_ROOT = SCRIPT_DIR.parent
PRACTICUM_ROOT = ANSWER_CARD_ROOT.parent
PROJECT_ROOT = PRACTICUM_ROOT.parent
DEFAULT_TEMPLATE_PATH = ANSWER_CARD_ROOT / "configs" / "answer_card_template.yaml"
DEFAULT_GRADER_CONFIG_PATH = PRACTICUM_ROOT / "grader-config.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid yaml: {path}")
    return data


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_template_config(path: Path | None = None) -> dict[str, Any]:
    template_path = path or DEFAULT_TEMPLATE_PATH
    return load_yaml(template_path)


def load_grader_config(path: Path | None = None) -> dict[str, Any]:
    grader_path = path or DEFAULT_GRADER_CONFIG_PATH
    return load_yaml(grader_path)


def phase1_workspace_path(template_config: dict[str, Any]) -> Path:
    workspace = template_config.get("workspace", {}) or {}
    raw_value = str(workspace.get("phase1_dir", "../workspace/phase1")).strip()
    return resolve_path(ANSWER_CARD_ROOT / "configs", raw_value)


def scanned_input_path(template_config: dict[str, Any]) -> Path:
    input_cfg = template_config.get("input", {}) or {}
    raw_value = str(input_cfg.get("scanned_dir", "../../workspace/practicum-batch/raw/软件需求答题卡扫描件")).strip()
    return resolve_path(ANSWER_CARD_ROOT / "configs", raw_value)


def ensure_phase1_dirs(workspace: Path) -> dict[str, Path]:
    dirs = {
        "root": workspace,
        "normalized": workspace / "normalized",
        "crops": workspace / "crops",
        "parsed": workspace / "parsed",
        "exports": workspace / "exports",
        "review": workspace / "review",
        "debug": workspace / "debug",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def iter_image_files(root: Path) -> list[Path]:
    supported = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sorted([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in supported])


def parse_paper_filename(path: Path) -> tuple[str, str]:
    stem = path.stem.strip()
    match = re.match(r"^\s*(\d+)_([^\\/:*?\"<>|]+?)\s*$", stem)
    if match:
        return match.group(1), match.group(2)
    return stem, ""


def paper_id_from_path(path: Path) -> str:
    student_number, student_name = parse_paper_filename(path)
    if student_name:
        return f"{student_number}_{student_name}"
    return student_number


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def pil_to_data_url(image: Image.Image, format_name: str = "PNG") -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=format_name)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/{format_name.lower()};base64,{encoded}"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def extract_json_object(text: str) -> dict[str, Any]:
    text = str(text or "").strip()
    if not text:
        raise ValueError("empty model response")

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"no json object found: {text[:300]}")
    snippet = text[start : end + 1]
    return json.loads(snippet)


def read_image(path: Path) -> Image.Image:
    image = Image.open(path)
    return image.convert("RGB")
