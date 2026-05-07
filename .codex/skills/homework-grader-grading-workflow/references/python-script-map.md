# Python Script Map

Python scripts are still part of the current system and may be called directly by backend config, local workflows, validation runs, or operator tooling. Do not delete or move them during documentation cleanup.

## Root `scripts/`

General grading and utility scripts:

- `batch_score.py`: general batch scoring workflow.
- `calibrate.py`: calibration support.
- `preprocess.py`: general preprocessing.
- `export_excel.py`: Excel export.
- `stats.py`: statistics.
- `debug_exam_crops.py`: exam crop debugging.
- `test_exam_gray_boxes.py`: answer-card/image detection test support.
- `generate_research_proposal_doc.py` and `create_research_proposal_doc.ps1`: document generation helper.
- `requirements.txt`: Python dependencies for root scripts.

These scripts relate to generic Rubric, Prompt, preprocessing, calibration, scoring, statistics, and export capabilities.

## `software-project-practicum/scripts/`

Current practicum workflow scripts:

- `preprocess_student_dirs.py`: configured by backend as `grader.python.preprocess-script`.
- `batch_score_reports.py`: configured by backend as `grader.python.grading-script`.
- `export_traceability_excel.py`: configured by backend as `grader.python.export-script`.
- `common.py`: shared helpers.
- `convert_doc_with_word.ps1`: Word conversion helper.

These are directly connected to `PythonScriptClient` through `application.yml`.

## `software-project-practicum/answer-card/scripts/`

Answer-card workflow scripts:

- `extract_scanned_scores.py`: extract scores or regions from scanned answer cards.
- `extract_subjective_samples.py`: prepare subjective samples.
- `infer_objective_answers.py`: infer objective answers.
- `infer_fill_blank_answers.py`: infer fill-in answers.
- `infer_subjective_rubric.py`: infer or build subjective Rubric support.
- `prepare_standard_build_dataset.py`: prepare standard-answer build dataset.
- `run_validation_scoring.py`: validation scoring run.
- `export_scores_excel.py`: score export.
- `export_validation_report.py`: validation report export.
- `generate_database_data_catalog_doc.py`: database/catalog documentation helper.
- `common.py`: shared answer-card helpers.

These scripts support answer-card grading, validation, standard answer construction, and export. They may not be wired to the Spring Boot backend yet, but they are not deprecated by default.

## Change Rule

When changing a Python script:

- identify whether backend config calls it;
- check expected working directory;
- check generated files under workspace/reports/scores;
- preserve model call configuration if present;
- document input/output format changes for backend and frontend consumers.
