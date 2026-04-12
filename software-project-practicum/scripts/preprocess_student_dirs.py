from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from common import (
    ROLE_ORDER,
    build_error_ir,
    build_student_ir,
    collect_student_dirs,
    collect_supported_files,
    detect_document_role,
    ensure_workspace_dirs,
    extract_text_document,
    load_config,
    parse_student_dir_name,
    save_student_mapping,
    source_file_for_workspace,
    workspace_path,
    write_json,
)

logger = logging.getLogger(__name__)


def _log_entry(step: str, status: str, message: str = "") -> dict[str, str]:
    return {
        "step": step,
        "status": status,
        "message": message,
    }


def process_student_dir(
    student_dir: Path,
    workspace: Path,
    student_id: str,
) -> dict:
    student_number, student_name = parse_student_dir_name(student_dir.name)
    processing_log: list[dict[str, str]] = []
    files = collect_supported_files(student_dir)
    source_files = [source_file_for_workspace(workspace, student_dir, file_path) for file_path in files]

    if not files:
        processing_log.append(_log_entry("collect_files", "error", "no supported files found"))
        return build_error_ir(
            student_id=student_id,
            student_number=student_number,
            student_name=student_name,
            source_files=[],
            error_type="no_supported_files",
            error_message="No supported .doc/.docx/.pdf files found in student directory",
            processing_log=processing_log,
        )

    documents: list[dict] = []
    converted_dir = workspace / "logs" / "converted-docs" / student_id

    for file_path in files:
        try:
            actual_path, extracted = extract_text_document(file_path, converted_dir)
            role = detect_document_role(file_path.name, extracted["full_text"]) or "unknown"
            extracted["role"] = role
            extracted["source_file"] = source_file_for_workspace(workspace, student_dir, file_path)
            documents.append(extracted)
            message = f"{file_path.name} -> role={role}, conversion={extracted.get('conversion_method', 'none')}"
            if actual_path != file_path:
                message += f", converted={actual_path.name}"
            processing_log.append(_log_entry("extract_document", "success", message))
        except Exception as exc:  # noqa: BLE001
            processing_log.append(_log_entry("extract_document", "error", f"{file_path.name}: {exc}"))
            return build_error_ir(
                student_id=student_id,
                student_number=student_number,
                student_name=student_name,
                source_files=source_files,
                error_type="document_extraction_failed",
                error_message=str(exc),
                processing_log=processing_log,
            )

    documents = sorted(
        [document for document in documents if document.get("role") in ROLE_ORDER or document.get("role") == "unknown"],
        key=lambda item: (
            ROLE_ORDER.index(item["role"]) if item["role"] in ROLE_ORDER else 99,
            str(item.get("source_file", "")),
        ),
    )
    if any(document.get("role") == "unknown" for document in documents):
        unknown_files = [str(document.get("source_file", "")) for document in documents if document.get("role") == "unknown"]
        processing_log.append(
            _log_entry("role_detection", "warning", f"unknown role files: {', '.join(unknown_files)}")
        )

    return build_student_ir(
        student_id=student_id,
        student_number=student_number,
        student_name=student_name,
        documents=documents,
        processing_log=processing_log,
    )


def run_batch(config_path: Path | None = None) -> None:
    config = load_config(config_path)
    effective_config = (config_path or Path(__file__).resolve().parents[1] / "grader-config.yaml").resolve()
    os.environ["GRADER_CONFIG_PATH"] = str(effective_config)
    workspace = workspace_path(config)
    ensure_workspace_dirs(workspace)

    raw_dir = workspace / "raw"
    ir_dir = workspace / "ir"
    mapping_path = workspace / "student-mapping.csv"

    student_dirs = collect_student_dirs(raw_dir)
    if not student_dirs:
        logger.warning("No student directories found in %s", raw_dir)
        return

    logger.info("Found %d student directories", len(student_dirs))

    mapping_rows: list[dict[str, str]] = []
    for index, student_dir in enumerate(student_dirs, start=1):
        student_id = f"anon-{index:03d}"
        logger.info("[%d/%d] Processing %s -> %s", index, len(student_dirs), student_dir.name, student_id)
        ir = process_student_dir(student_dir, workspace, student_id)
        write_json(ir_dir / f"{student_id}.json", ir)
        student_number = str(ir.get("metadata", {}).get("student_number", ""))
        student_name = str(ir.get("metadata", {}).get("student_name", ""))
        mapping_rows.append(
            {
                "anon_id": student_id,
                "student_number": student_number,
                "name": student_name,
            }
        )

    save_student_mapping(mapping_path, mapping_rows)
    logger.info("Wrote %d IR files to %s", len(student_dirs), ir_dir)
    logger.info("Wrote student mapping to %s", mapping_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess student directories into student-level IR JSON.")
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
    run_batch(args.config)


if __name__ == "__main__":
    main()
