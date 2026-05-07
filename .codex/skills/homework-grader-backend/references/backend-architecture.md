# Backend Architecture

## Source Of Truth

Current backend code lives in `software-project-practicum/backend/`.

Checked files:

- `pom.xml`
- `src/main/resources/application.yml`
- `src/main/java/com/homeworkgrader/controller/`
- `src/main/java/com/homeworkgrader/service/`
- `src/main/java/com/homeworkgrader/repository/`
- `src/main/java/com/homeworkgrader/client/python/`
- `src/main/java/com/homeworkgrader/storage/`
- `src/main/java/com/homeworkgrader/config/`

Technology stack is code-first. Current `pom.xml` uses Spring Boot `2.7.18` and Java `1.8`. If any document claims Spring Boot 3 or Java 17, treat it as a documentation conflict and report it before implementing.

## Runtime Configuration

`application.yml` defines:

- `server.port: 8080`
- MySQL datasource: `jdbc:mysql://localhost:3306/homework_grader`
- Multipart limits: `100MB` per file, `500MB` per request.
- Swagger UI path: `/swagger-ui.html`
- `grader.workspace-root: ../workspace/practicum-batch`
- `grader.python.executable: ../../.venv/Scripts/python.exe`
- `grader.python.working-directory: ..`
- `grader.python.preprocess-script: scripts/preprocess_student_dirs.py`
- `grader.python.grading-script: scripts/batch_score_reports.py`
- `grader.python.export-script: scripts/export_traceability_excel.py`

Do not remove `grader.python.*` unless the user explicitly asks to migrate the workflow.

## Main Packages

- `controller/`: REST controllers for auth, base data, courses, assessments, submissions, grading, export, and frontend prototype adapter APIs.
- `service/`: application services for auth, organization, submissions, and grading workflow orchestration.
- `repository/CrudJdbcRepository.java`: generic JDBC repository with an allowlist of known tables and identifier validation.
- `client/python/PythonScriptClient.java`: invokes configured Python scripts through `ProcessBuilder` and returns script, timing, exit code, stdout, and stderr.
- `storage/FileStorageService.java`: stores uploaded submissions under the workspace root, sanitizes filenames, checks path traversal, computes SHA-256, and resolves report files.
- `config/`: CORS, session auth interceptor, and `GraderProperties`.

## Authentication And Web Config

`AuthInterceptor` checks HTTP session attribute `AuthService.SESSION_USER_ID` for `/api/**`. It excludes:

- `/api/auth/login`
- `/api/auth/logout`
- `/swagger-ui.html`
- `/swagger-ui/**`
- `/v3/api-docs/**`

`WebMvcConfig` enables CORS for `http://localhost:*` and `http://127.0.0.1:*` with credentials.

## Data Access

`CrudJdbcRepository` allows CRUD access only for explicitly listed tables:

`organization_unit`, `teacher`, `student`, `course`, `course_offering`, `teaching_class`, `course_offering_teacher`, `teaching_class_student`, `assessment`, `assessment_template`, `question_definition`, `rubric_definition`, `standard_answer`, `answer_card_layout`, `submission`, `submission_asset`, `extraction_run`, `extraction_result`, `grading_run`, `score_item_result`, `final_result`, `course_grade`, `grade_publish_record`.

It is intentionally simple JDBC. Do not introduce schema-wide ORM changes for small feature work.

## Grading Workflow

`GradingWorkflowService` starts an async workflow per assessment id:

1. Marks status `QUEUED`.
2. Runs `PythonScriptClient.runPreprocess()`.
3. Runs `PythonScriptClient.runGrading()` if preprocessing succeeds.
4. Stores in-memory progress as `PREPROCESSING`, `GRADING`, `COMPLETED`, or `FAILED`.

Teacher review operations update `final_result`:

- `confirm` sets `review_status` to `CONFIRMED` and stores `confirmed_by_teacher_id`.
- `adjust` can update `final_score`, sets `score_source` to `TEACHER_ADJUSTED`, and sets `review_status` to `ADJUSTED`.

Audit-sensitive changes must preserve or improve traceability. Current code does not set `confirmed_at` during confirmation; treat that as a potential improvement area, not something to hide.

## Upload And Export

`SubmissionService.upload` creates:

- a `submission` row with incremented `attempt_no`;
- a stored original file under `raw/assessment-{id}/student-{id}/`;
- a `submission_asset` row with file name, extension, path, hash, size, and version.

`ExportController` runs the configured export script, then selects the latest `.xlsx` file from `reportsRoot()`. `/api/reports/latest/download` returns the newest report file.

## Known Code Notes

Several Java string literals appear mojibake when read through the shell. Do not “fix” encoding opportunistically during unrelated backend work. If a task involves user-facing messages, inspect and test encoding deliberately.
