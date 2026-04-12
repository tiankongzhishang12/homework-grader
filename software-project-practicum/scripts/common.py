from __future__ import annotations

import csv
import importlib.util
import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PRACTICUM_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PRACTICUM_ROOT / "grader-config.yaml"
WORKSPACE_DEFAULT = PRACTICUM_ROOT / "workspace" / "practicum-batch"

SUPPORTED_TEXT_EXTENSIONS = {".doc", ".docx", ".pdf"}
ROLE_ORDER = ["requirements", "hld", "lld"]
ROLE_LABELS = {
    "requirements": "需求规格说明书",
    "hld": "项目概要设计说明书",
    "lld": "项目详细设计说明书",
}
ROLE_PATTERNS = {
    "requirements": ["需求规格说明书", "需求说明", "需求分析"],
    "hld": ["概要设计说明书", "概要设计"],
    "lld": ["详细设计说明书", "详细设计"],
}
EXCLUDED_HEADING_KEYWORDS = [
    "实现截图",
    "运行结果",
    "系统运行",
    "功能实现",
    "实训体会",
    "体会和收获",
    "收获",
]
RELEVANT_IMAGE_KEYWORDS = [
    "用例图",
    "活动图",
    "系统用例图",
    "架构图",
    "系统架构",
    "时序图",
    "顺序图",
    "类图",
    "er图",
    "数据库",
    "界面原型",
    "原型图",
    "页面设计",
    "界面设计",
]
SCREENSHOT_KEYWORDS = [
    "实现截图",
    "运行截图",
    "系统首页",
    "功能实现",
    "登录实现",
    "点击",
    "返回首页",
]
PLACEHOLDER_PATTERNS = [
    "采用用例规约表",
    "流程图如下",
    "请在此处补充",
    "请补充",
    "如下图所示",
    "根据模板补充",
    "此处填写",
    "此处补充",
    "待补充",
    "待完善",
    "模板说明",
]
PLACEHOLDER_STRIP_PATTERNS = PLACEHOLDER_PATTERNS + [
    "参考如下",
    "见下图",
    "见下表",
    "本节内容",
    "说明如下",
]

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "contribution": ["分工", "本人负责", "负责模块", "负责功能"],
    "req_usecase": ["用例规约", "用例表", "用例图", "涉众", "角色", "系统用例"],
    "req_flow": ["活动图", "业务流程", "流程", "流程图"],
    "hld_sequence": ["时序", "顺序", "交互"],
    "ui": ["界面", "页面", "原型", "首页", "登录页", "注册页"],
    "class": ["类图", "类设计", "业务类", "实体类", "service", "mapper", "controller"],
    "api": ["接口", "api", "controller"],
    "database": ["数据库", "数据表", "表设计", "er图", "实体关系"],
    "method_flow": ["方法", "算法", "实现流程", "流程图", "复杂逻辑"],
}
TOPIC_DETAIL_MARKERS: dict[str, list[str]] = {
    "req_usecase": ["参与者", "前置条件", "基本事件流", "异常流", "后置条件"],
    "req_flow": ["开始", "结束", "判断", "流转", "状态", "步骤"],
    "hld_sequence": ["controller", "service", "mapper", "调用", "返回", "时序", "交互"],
    "ui": ["输入", "按钮", "列表", "校验", "跳转", "展示", "功能"],
    "class": ["属性", "方法", "职责", "关联", "service", "mapper", "controller", "entity"],
    "api": ["url", "get", "post", "put", "delete", "请求", "响应", "参数", "返回", "状态码"],
    "database": ["表名", "字段", "主键", "外键", "类型", "长度", "约束", "索引"],
    "method_flow": ["参数", "返回", "步骤", "判断", "分支", "算法", "逻辑"],
    "contribution": ["负责", "模块", "页面", "接口", "数据库", "类", "设计"],
}
TOPIC_EMPTY_SHELL_THRESHOLDS = {
    "req_usecase": 120,
    "req_flow": 100,
    "hld_sequence": 100,
    "ui": 90,
    "class": 100,
    "api": 100,
    "database": 100,
    "method_flow": 100,
    "contribution": 60,
}
TOPIC_DEFAULTS_BY_ROLE = {
    "requirements": ("req_usecase", "req_flow"),
    "hld": ("hld_sequence",),
    "lld": ("ui", "class", "api", "database", "method_flow"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config: {path}")
    return data


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def workspace_path(config: dict[str, Any]) -> Path:
    grading = config.get("grading", {})
    raw_value = str(grading.get("workspace_path", "")).strip()
    if not raw_value:
        return WORKSPACE_DEFAULT
    return resolve_path(PRACTICUM_ROOT, raw_value)


def rubric_path(config: dict[str, Any]) -> Path:
    grading = config.get("grading", {})
    raw_value = str(grading.get("rubric_path", "")).strip()
    if not raw_value:
        return PRACTICUM_ROOT / "rubrics" / "software-project-traceability-rubric.yaml"
    return resolve_path(PRACTICUM_ROOT, raw_value)


def model_name(config: dict[str, Any]) -> str:
    openai = config.get("openai", {})
    return str(openai.get("model", "")).strip() or "gpt-5.4"


def worker_count(config: dict[str, Any]) -> int:
    grading = config.get("grading", {})
    try:
        return int(grading.get("workers", 3))
    except Exception:
        return 3


def ensure_workspace_dirs(workspace: Path) -> None:
    for name in ["raw", "reference", "ir", "scores", "reports", "logs"]:
        (workspace / name).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=8)
def load_root_module(module_name: str, relative_path: str):
    file_path = PROJECT_ROOT / relative_path
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    scripts_dir = str(PROJECT_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def preprocess_module():
    return load_root_module("practicum_base_preprocess", "scripts/preprocess.py")


def batch_score_module():
    return load_root_module("practicum_base_batch_score", "scripts/batch_score.py")


def export_excel_module():
    return load_root_module("practicum_base_export_excel", "scripts/export_excel.py")


def parse_student_dir_name(name: str) -> tuple[str, str]:
    match = re.match(r'^\s*(\d+)_([^\\/:*?"<>|]+?)\s*$', name)
    if match:
        return match.group(1), match.group(2)
    return name, ""


def collect_student_dirs(raw_dir: Path) -> list[Path]:
    return sorted([path for path in raw_dir.iterdir() if path.is_dir()], key=lambda p: p.name)


def collect_supported_files(student_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in student_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS
        ],
        key=lambda p: p.name.lower(),
    )


def detect_document_role(file_name: str, preview_text: str) -> str | None:
    for role, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if pattern in file_name:
                return role
    preview = preview_text[:2000]
    for role, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if pattern in preview:
                return role
    return None


def is_scoring_section(heading: str) -> bool:
    if not heading.strip():
        return True
    return not any(keyword in heading for keyword in EXCLUDED_HEADING_KEYWORDS)


def is_relevant_image(image_entry: dict[str, Any]) -> bool:
    combined = " ".join(
        str(image_entry.get(key, "") or "")
        for key in ("caption", "context", "description", "extracted_text", "type")
    ).lower()
    if any(keyword.lower() in combined for keyword in SCREENSHOT_KEYWORDS):
        return False
    return any(keyword.lower() in combined for keyword in RELEVANT_IMAGE_KEYWORDS)


def detect_placeholder_signals(text: str) -> list[str]:
    return [pattern for pattern in PLACEHOLDER_PATTERNS if pattern in text]


def normalize_detail_text(text: str) -> str:
    cleaned = text
    for pattern in PLACEHOLDER_STRIP_PATTERNS:
        cleaned = cleaned.replace(pattern, " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def init_topic_stats() -> dict[str, dict[str, int]]:
    topics = sorted(
        set(TOPIC_KEYWORDS) | set(TOPIC_DETAIL_MARKERS) | set(TOPIC_EMPTY_SHELL_THRESHOLDS)
    )
    return {
        topic: {
            "placeholder_only_count": 0,
            "mixed_count": 0,
            "valid_count": 0,
        }
        for topic in topics
    }


def merge_topic_stats(base: dict[str, dict[str, int]], extra: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    merged = init_topic_stats()
    for source in (base, extra):
        for topic, counters in source.items():
            bucket = merged.setdefault(
                topic,
                {"placeholder_only_count": 0, "mixed_count": 0, "valid_count": 0},
            )
            for key in ("placeholder_only_count", "mixed_count", "valid_count"):
                bucket[key] = int(bucket.get(key, 0) or 0) + int(counters.get(key, 0) or 0)
    return merged


def classify_topic(role: str, heading: str, text: str) -> str | None:
    combined = f"{heading} {text}".lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword.lower() in combined for keyword in keywords):
            return topic

    for topic in TOPIC_DEFAULTS_BY_ROLE.get(role, ()):
        heading_lower = heading.lower()
        if topic == "req_usecase" and any(keyword in heading for keyword in ("用例", "涉众", "角色")):
            return topic
        if topic == "req_flow" and any(keyword in heading for keyword in ("流程", "活动", "系统用例")):
            return topic
        if topic == "hld_sequence" and any(keyword in heading for keyword in ("时序", "交互", "顺序")):
            return topic
        if topic == "ui" and any(keyword in heading for keyword in ("界面", "页面", "原型")):
            return topic
        if topic == "class" and any(keyword in heading_lower for keyword in ("类", "service", "mapper", "controller")):
            return topic
        if topic == "api" and any(keyword in heading_lower for keyword in ("接口", "api", "controller")):
            return topic
        if topic == "database" and any(keyword in heading_lower for keyword in ("数据库", "表", "er")):
            return topic
        if topic == "method_flow" and any(keyword in heading for keyword in ("方法", "流程", "算法")):
            return topic
    return None


def has_topic_details(topic: str, heading: str, text: str) -> bool:
    normalized = normalize_detail_text(text)
    combined = f"{heading} {normalized}".lower()
    if len(normalized) >= 220:
        return True

    hit_count = sum(1 for marker in TOPIC_DETAIL_MARKERS.get(topic, []) if marker.lower() in combined)
    if hit_count >= 2:
        return True

    if topic == "api" and re.search(r"/[A-Za-z0-9_\-/]+", normalized):
        return True
    if topic == "database" and normalized.count("|") >= 2:
        return True
    if topic in {"req_usecase", "req_flow", "method_flow"} and re.search(r"(1\.|2\.|3\.|第一步|第二步)", normalized):
        return True
    return False


def analyze_scoring_section(role: str, section: dict[str, Any]) -> dict[str, Any]:
    heading = str(section.get("heading", "")).strip()
    text = str(section.get("text", "")).strip()
    combined = "\n".join(part for part in [heading, text] if part).strip()
    topic = classify_topic(role, heading, text)
    signals = detect_placeholder_signals(combined)
    has_detail = has_topic_details(topic, heading, text) if topic else False
    normalized = normalize_detail_text(text)
    threshold = TOPIC_EMPTY_SHELL_THRESHOLDS.get(topic or "", 100)
    looks_like_shell = bool(topic) and bool(text) and len(normalized) < threshold and not has_detail
    heading_indicates_structured_content = any(
        keyword in heading for keyword in ("表", "图", "用例", "接口", "方法", "数据库", "类", "流程")
    )

    section_type = "valid_section"
    if signals and not has_detail:
        section_type = "placeholder_only_section"
    elif signals and has_detail:
        section_type = "mixed_section"
    elif looks_like_shell and heading_indicates_structured_content:
        section_type = "placeholder_only_section"

    return {
        **section,
        "topic": topic,
        "section_type": section_type,
        "placeholder_signals": signals,
        "normalized_text_length": len(normalized),
    }


def analyze_document_sections(
    role: str, sections: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, int]]]:
    analyzed_sections: list[dict[str, Any]] = []
    placeholder_sections: list[dict[str, Any]] = []
    topic_stats = init_topic_stats()

    for section in sections:
        analyzed = analyze_scoring_section(role, section)
        analyzed_sections.append(analyzed)

        topic = analyzed.get("topic")
        if topic:
            bucket = topic_stats.setdefault(
                topic,
                {"placeholder_only_count": 0, "mixed_count": 0, "valid_count": 0},
            )
            section_type = str(analyzed.get("section_type", "valid_section"))
            if section_type == "placeholder_only_section":
                bucket["placeholder_only_count"] += 1
            elif section_type == "mixed_section":
                bucket["mixed_count"] += 1
            else:
                bucket["valid_count"] += 1

        if analyzed.get("section_type") in {"placeholder_only_section", "mixed_section"}:
            placeholder_sections.append(
                {
                    "heading": str(analyzed.get("heading", "")).strip(),
                    "topic": analyzed.get("topic"),
                    "section_type": analyzed.get("section_type"),
                    "signals": list(analyzed.get("placeholder_signals", []) or []),
                    "snippet": str(analyzed.get("text", "")).strip()[:180],
                }
            )

    return analyzed_sections, placeholder_sections, topic_stats


def source_file_for_workspace(workspace: Path, student_dir: Path, file_path: Path) -> str:
    _ = student_dir
    return file_path.relative_to(workspace).as_posix()


def convert_doc_with_word(source_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_path.stem}.docx"
    script_path = PRACTICUM_ROOT / "scripts" / "convert_doc_with_word.ps1"
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        str(source_path),
        str(output_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not output_path.exists():
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"Word conversion failed: {source_path.name}")
    return output_path


def extract_text_document(file_path: Path, converted_dir: Path) -> tuple[Path, dict[str, Any]]:
    preprocess = preprocess_module()
    actual_path = file_path
    conversion_method = "none"
    if file_path.suffix.lower() == ".doc":
        actual_path = convert_doc_with_word(file_path, converted_dir)
        conversion_method = "word"

    if actual_path.suffix.lower() == ".docx":
        full_text, sections = preprocess.extract_docx(actual_path)
        try:
            images = preprocess.extract_docx_images(actual_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract embedded images from %s: %s", actual_path.name, exc)
            images = []
    else:
        full_text, sections = preprocess.extract_pdf(actual_path)
        images = []

    metadata = preprocess.extract_text_metadata(full_text, sections)
    filtered_images = [entry for entry in images if is_relevant_image(entry)]
    section_payload = [
        {"heading": section.heading, "level": section.level, "text": section.text}
        for section in sections
    ]
    role = detect_document_role(file_path.name, full_text) or ""
    analyzed_sections, placeholder_sections, topic_stats = analyze_document_sections(role, section_payload)
    return actual_path, {
        "title": next((section.heading for section in sections if section.heading.strip()), actual_path.stem),
        "full_text": full_text,
        "sections": analyzed_sections,
        "images": filtered_images,
        "metadata": {
            "word_count": metadata.word_count,
            "paragraph_count": metadata.paragraph_count,
            "heading_count": metadata.heading_count,
            "has_references": metadata.has_references,
            "language": metadata.language,
            "image_count": len(filtered_images),
            "placeholder_sections": placeholder_sections,
            "placeholder_count": len(placeholder_sections),
            "topic_stats": topic_stats,
        },
        "evidence_quality": "complete" if full_text.strip() else "partial",
        "conversion_method": conversion_method,
        "converted_file": str(actual_path) if actual_path != file_path else "",
    }


def iter_scoring_sections(document: dict[str, Any]) -> list[dict[str, Any]]:
    sections = document.get("sections", [])
    filtered = [section for section in sections if is_scoring_section(str(section.get("heading", "")))]
    if filtered:
        return filtered
    full_text = str(document.get("full_text", "")).strip()
    if not full_text:
        return []
    return [{"heading": "", "level": 1, "text": full_text, "section_type": "valid_section"}]


def build_student_answer(documents: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for role in ROLE_ORDER:
        matched = [document for document in documents if document.get("role") == role]
        if not matched:
            continue
        parts.append(f"# {ROLE_LABELS[role]}")
        for document in matched:
            title = str(document.get("title", "")).strip()
            if title and title != ROLE_LABELS[role]:
                parts.append(f"## {title}")
            for section in iter_scoring_sections(document):
                heading = str(section.get("heading", "")).strip()
                level = int(section.get("level", 1) or 1)
                text = str(section.get("text", "")).strip()
                if heading:
                    prefix = "#" * min(max(level + 1, 2), 6)
                    parts.append(f"{prefix} {heading}")
                if text:
                    parts.append(text)
            for index, image_entry in enumerate(document.get("images", []), start=1):
                caption = str(image_entry.get("caption", "")).strip() or f"{ROLE_LABELS[role]}图示{index}"
                description = str(image_entry.get("description", "")).strip()
                context = str(image_entry.get("context", "")).strip()
                image_lines = [f"### 图示 {index}: {caption}"]
                if description:
                    image_lines.append(description)
                if context:
                    image_lines.append(f"图示上下文: {context}")
                parts.append("\n".join(image_lines))
    return "\n\n".join(part for part in parts if part.strip()).strip()


def render_ir_for_scoring(ir: dict[str, Any]) -> str:
    documents = list(ir.get("content", {}).get("documents", []))
    placeholder_total = sum(
        int(document.get("metadata", {}).get("placeholder_count", 0) or 0) for document in documents
    )
    parts: list[str] = [
        "## Submission Metadata",
        f"- Student ID: {ir.get('student_id', 'unknown')}",
        f"- Roles present: {', '.join(ir.get('metadata', {}).get('document_roles_present', []))}",
        f"- Placeholder-like sections detected: {placeholder_total}",
    ]

    topic_stats = ir.get("metadata", {}).get("topic_stats", {}) or {}
    if topic_stats:
        parts.append("## Placeholder Topic Stats")
        for topic, counters in topic_stats.items():
            if sum(int(counters.get(key, 0) or 0) for key in ("placeholder_only_count", "mixed_count", "valid_count")) <= 0:
                continue
            parts.append(
                f"- {topic}: valid={int(counters.get('valid_count', 0) or 0)}, "
                f"mixed={int(counters.get('mixed_count', 0) or 0)}, "
                f"placeholder_only={int(counters.get('placeholder_only_count', 0) or 0)}"
            )

    for role in ROLE_ORDER:
        matched = [document for document in documents if document.get("role") == role]
        if not matched:
            continue
        parts.append(f"## {ROLE_LABELS[role]}")
        for document in matched:
            parts.append(f"### Source File: {document.get('source_file', '')}")
            title = str(document.get("title", "")).strip()
            if title:
                parts.append(f"Document Title: {title}")

            placeholder_sections = list(document.get("metadata", {}).get("placeholder_sections", []) or [])
            if placeholder_sections:
                placeholder_lines = ["### Ignored Placeholder Sections"]
                for item in placeholder_sections[:8]:
                    heading = str(item.get("heading", "")).strip() or "未命名章节"
                    topic = str(item.get("topic", "")).strip()
                    section_type = str(item.get("section_type", "")).strip()
                    signals = ", ".join(str(signal) for signal in item.get("signals", []) if str(signal).strip())
                    snippet = str(item.get("snippet", "")).strip()
                    line = f"- 章节: {heading}"
                    if topic:
                        line += f" | 主题: {topic}"
                    if section_type:
                        line += f" | 类型: {section_type}"
                    if signals:
                        line += f" | 信号: {signals}"
                    if snippet:
                        line += f" | 摘录: {snippet}"
                    placeholder_lines.append(line)
                parts.append("\n".join(placeholder_lines))

            for section in iter_scoring_sections(document):
                heading = str(section.get("heading", "")).strip()
                level = int(section.get("level", 1) or 1)
                text = str(section.get("text", "")).strip()
                section_type = str(section.get("section_type", "valid_section"))
                if heading:
                    prefix = "#" * min(max(level, 2), 6)
                    parts.append(f"{prefix} {heading}")
                if section_type == "placeholder_only_section":
                    parts.append("该章节仅包含模板占位内容，不能作为评分证据。")
                elif text:
                    parts.append(text)

            images = list(document.get("images", []))
            if images:
                image_blocks = ["### Relevant Images / Diagrams"]
                for index, image_entry in enumerate(images, start=1):
                    caption = str(image_entry.get("caption", "")).strip() or f"图示{index}"
                    description = str(image_entry.get("description", "")).strip()
                    context = str(image_entry.get("context", "")).strip()
                    block_lines = [f"- {caption}"]
                    if description:
                        block_lines.append(f"  描述: {description}")
                    if context:
                        block_lines.append(f"  上下文: {context}")
                    image_blocks.append("\n".join(block_lines))
                parts.append("\n".join(image_blocks))
    return "\n\n".join(part for part in parts if str(part).strip()).strip()


def build_gate_results(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roles_present = sorted({str(document.get("role", "")) for document in documents if document.get("role")})
    role_counts = {
        role: sum(1 for document in documents if document.get("role") == role)
        for role in roles_present
    }

    missing_roles = [role for role in ROLE_ORDER if role not in roles_present]
    duplicates = [role for role, count in role_counts.items() if count > 1]

    return [
        {
            "gate_id": "G-001",
            "gate_name": "需求文档存在性",
            "passed": "requirements" in roles_present,
            "details": "requirements present" if "requirements" in roles_present else "requirements missing",
            "on_fail": "flag",
        },
        {
            "gate_id": "G-002",
            "gate_name": "概要设计文档存在性",
            "passed": "hld" in roles_present,
            "details": "hld present" if "hld" in roles_present else "hld missing",
            "on_fail": "flag",
        },
        {
            "gate_id": "G-003",
            "gate_name": "详细设计文档存在性",
            "passed": "lld" in roles_present,
            "details": "lld present" if "lld" in roles_present else "lld missing",
            "on_fail": "flag",
        },
        {
            "gate_id": "G-004",
            "gate_name": "重复角色文档检查",
            "passed": not duplicates,
            "details": "no duplicate roles" if not duplicates else f"duplicate roles: {', '.join(duplicates)}",
            "on_fail": "warn",
        },
        {
            "gate_id": "G-005",
            "gate_name": "三类文档完整性",
            "passed": not missing_roles,
            "details": "all core roles present" if not missing_roles else f"missing roles: {', '.join(missing_roles)}",
            "on_fail": "flag",
        },
    ]


def save_student_mapping(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["anon_id", "student_number", "name"])
        writer.writeheader()
        writer.writerows(rows)


def build_student_ir(
    student_id: str,
    student_number: str,
    student_name: str,
    documents: list[dict[str, Any]],
    processing_log: list[dict[str, Any]],
) -> dict[str, Any]:
    merged_images: list[dict[str, Any]] = []
    source_files: list[str] = []
    placeholder_count = 0
    topic_stats = init_topic_stats()

    for document in documents:
        merged_images.extend(document.get("images", []))
        source_files.append(document.get("source_file", ""))
        placeholder_count += int(document.get("metadata", {}).get("placeholder_count", 0) or 0)
        topic_stats = merge_topic_stats(topic_stats, document.get("metadata", {}).get("topic_stats", {}) or {})

    roles_present = [role for role in ROLE_ORDER if any(doc.get("role") == role for doc in documents)]
    merged_text = build_student_answer(documents)
    evidence_quality = "complete"
    if any(document.get("evidence_quality") != "complete" for document in documents):
        evidence_quality = "partial"

    content_documents = [
        {
            "role": document.get("role"),
            "source_file": document.get("source_file"),
            "title": document.get("title"),
            "full_text": document.get("full_text"),
            "sections": document.get("sections"),
            "images": document.get("images"),
            "metadata": document.get("metadata"),
            "evidence_quality": document.get("evidence_quality"),
            "conversion_method": document.get("conversion_method", "none"),
            "converted_file": document.get("converted_file", ""),
        }
        for document in documents
    ]

    return {
        "student_id": student_id,
        "submission_type": "text",
        "source_files": source_files,
        "extracted_at": now_iso(),
        "metadata": {
            "student_number": student_number,
            "student_name": student_name,
            "document_count": len(documents),
            "document_roles_present": roles_present,
            "word_count": sum(int(doc.get("metadata", {}).get("word_count", 0) or 0) for doc in documents),
            "image_count": len(merged_images),
            "placeholder_count": placeholder_count,
            "topic_stats": topic_stats,
        },
        "content": {
            "documents": content_documents,
            "student_answer": merged_text,
            "full_text": merged_text,
            "assignment_text": "",
            "evidence_quality": evidence_quality,
            "images": merged_images,
        },
        "gate_results": build_gate_results(documents),
        "processing_log": processing_log,
    }


def build_error_ir(
    student_id: str,
    student_number: str,
    student_name: str,
    source_files: list[str],
    error_type: str,
    error_message: str,
    processing_log: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "submission_type": "text",
        "source_files": source_files,
        "extracted_at": now_iso(),
        "metadata": {
            "student_number": student_number,
            "student_name": student_name,
            "document_count": 0,
            "document_roles_present": [],
            "error_type": error_type,
            "error_message": error_message,
            "word_count": 0,
            "image_count": 0,
            "placeholder_count": 0,
            "topic_stats": init_topic_stats(),
        },
        "content": {
            "documents": [],
            "student_answer": "",
            "full_text": "",
            "assignment_text": "",
            "evidence_quality": "partial",
            "images": [],
        },
        "gate_results": [],
        "processing_log": processing_log,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
