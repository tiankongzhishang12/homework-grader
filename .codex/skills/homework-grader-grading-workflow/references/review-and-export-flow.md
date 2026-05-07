# Review And Export Flow

## Teacher Review

Teacher-facing review should expose:

- student identity and task context;
- original submission or derived asset reference;
- extracted content when available;
- per-item score, max score, evidence, confidence, and comments;
- review status and risk flags;
- final score source;
- teacher confirmation or adjustment action.

## Final Result

`final_result` is the final per-submission grade anchor:

- `submission_id`
- `selected_grading_run_id`
- `final_score`
- `score_source`
- `review_status`
- `confirmed_by_teacher_id`
- `confirmed_at`

Current backend confirmation updates review status and confirming teacher id. If improving auditability, consider setting `confirmed_at` as part of the same operation.

## Score Adjustment

Adjustments should preserve:

- original AI/batch grading run;
- prior score item evidence;
- final adjusted score;
- teacher identity where available;
- reason or comment when product requirements call for it.

Do not overwrite grading evidence to make adjusted results look machine-generated.

## Export

Current backend export:

1. Calls `PythonScriptClient.runExport()`.
2. Finds latest `.xlsx` under `FileStorageService.reportsRoot()`.
3. Returns report metadata or latest report download.

Export behavior should make data source and generation time clear. For grade publishing, preserve `grade_publish_record` or equivalent audit information.

## Quality Gates

Before considering grading/export complete:

- all submissions have known status;
- failed preprocessing or grading runs are visible;
- low-confidence or needs-review items remain reviewable;
- final results are distinguishable from raw grading runs;
- exported data matches confirmed or intended result source;
- generated files are traceable to run/config/version where feasible.
