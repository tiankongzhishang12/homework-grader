# Grading Domain Architecture

## Core Flow

1. Configure course, teaching class, assessment, template, questions, standard answers, Rubrics, answer-card layout, workspace, and export template.
2. Import or upload student submissions.
3. Store original assets with stable paths, file hash, size, type, and version.
4. Preprocess submissions through Java services and/or configured Python scripts.
5. Record extraction runs and extraction results where OCR, VLM, parser, or document conversion is used.
6. Run AI or batch grading against standard answers and Rubrics.
7. Store grading runs with model, run type, grading mode, rubric version, total score, confidence, and status.
8. Store score item results with score, max score, correctness, review flag, confidence, evidence, and comments.
9. Build final results for teacher confirmation or adjustment.
10. Export score sheets, traceability reports, validation reports, or course grades.

## Current Backend Orchestration

`GradingWorkflowService` currently runs:

- `PythonScriptClient.runPreprocess()`
- `PythonScriptClient.runGrading()`
- `GradingResultImportService.importScores(assessmentId)` after grading succeeds

`GradingResultImportService` reads `grader.workspace-root/student-mapping.csv` and `grader.workspace-root/scores/*.json`, maps anonymous ids such as `anon-001` to `student.student_no`, finds the latest submission for the assessment/student pair, and writes `grading_run`, `score_item_result`, and `final_result`.

Progress is stored in memory per assessment id and includes `importSummary` after import. Export uses `PythonScriptClient.runExport()` from `ExportController`.

Current limitations:

- Import skips score files when student mapping, student master data, or submission matching is missing.
- `score_item_result` currently stores rubric/question foreign keys as null unless a stable mapping is added later.
- Export still reads workspace score files through Python, rather than exporting directly from MySQL `final_result`.

## Data Model Anchors

- Configuration: `assessment`, `assessment_template`, `question_definition`, `rubric_definition`, `standard_answer`, `answer_card_layout`.
- Submission: `submission`, `submission_asset`.
- Extraction: `extraction_run`, `extraction_result`.
- Scoring: `grading_run`, `score_item_result`.
- Review: `final_result`.
- Course aggregation and publishing: `course_grade`, `grade_publish_record`.

## Quality Control

Use quality control for:

- low confidence scores;
- missing or malformed submissions;
- extraction failures;
- abnormal score distribution;
- answer-card region detection failures;
- model output that lacks evidence or violates schema;
- teacher adjustment patterns that reveal rubric or prompt drift.

Do not allow AI grading to erase evidence or teacher review paths.
