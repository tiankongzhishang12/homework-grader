# Backend API Map

This map is based on current controller annotations under `software-project-practicum/backend/src/main/java/com/homeworkgrader/controller/`.

## AuthController

Base path: `/api/auth`

- `POST /login`
- `GET /me`
- `POST /logout`

## BaseDataController

Base path: `/api`

- `GET /org/tree`
- `GET /teachers`
- `POST /teachers`
- `GET /students`
- `POST /students/import`

## CourseController

Base path: `/api`

- `GET /courses`
- `POST /courses`
- `GET /course-offerings`
- `POST /course-offerings`
- `GET /teaching-classes/{id}/students`

## AssessmentController

Base path: `/api`

- `GET /assessments`
- `POST /assessments`
- `GET /assessments/{id}`
- `POST /assessments/{id}/templates`
- `POST /templates/{id}/questions`
- `POST /templates/{id}/rubrics`

## StandardAnswerController

Base path: `/api`

- `POST /questions/{questionId}/standard-answers`
- `GET /questions/{questionId}/standard-answers`
- `GET /standard-answers/{id}`

## SubmissionController

Base path: `/api`

- `POST /assessments/{id}/submissions/upload`
- `GET /assessments/{id}/submissions`
- `GET /submissions/{id}`
- `GET /submissions/{id}/assets/{assetId}/download`

## GradingController

Base path: `/api`

- `POST /assessments/{id}/grading/start`
- `POST /assessments/{id}/grading/import-scores`
- `GET /assessments/{id}/grading/progress`
- `GET /grading-runs/{id}`
- `GET /submissions/{id}/score-items`
- `GET /assessments/{id}/final-results`
- `PUT /final-results/{id}/confirm`
- `PUT /final-results/{id}/adjust`
- `POST /assessments/{id}/grades/publish`

`PUT /api/final-results/{id}/confirm` updates `review_status = CONFIRMED`, `confirmed_by_teacher_id`, and `confirmed_at`. `PUT /api/final-results/{id}/adjust` is separate and is not changed by confirmation behavior.

Assessment grading start/progress is the real backend main-flow path. `POST /api/assessments/{id}/grading/start` now returns a progress object with:

- `assessmentId`
- `status`
- `message`
- `scriptResult`
- `importSummary`
- `startedAt`
- `updatedAt`

After `PythonScriptClient.runGrading()` succeeds, `GradingWorkflowService` calls `GradingResultImportService.importScores(assessmentId)`. The import service reads `grader.workspace-root/student-mapping.csv` and `grader.workspace-root/scores/*.json`, then writes matched results into `grading_run`, `score_item_result`, and `final_result`. Unmatched score files are skipped and recorded in `importSummary`; import failures set progress to `FAILED`.

`GET /api/assessments/{id}/grading/progress` returns the same shape. Current progress state is kept in memory by `GradingWorkflowService`; later production hardening should persist grading progress to database-backed run records.

`POST /api/assessments/{id}/grading/import-scores` is a development acceptance / demo debugging endpoint. It directly calls `GradingResultImportService.importScores(assessmentId)` to verify the workspace score JSON database import path. It does not run Python preprocessing and does not run real Python grading. Response data includes `assessmentId`, `status`, `message`, and `importSummary`. Production hardening should add permission control or restrict this endpoint to development environments only.

## ExportController

Base path: `/api`

- `POST /assessments/{id}/grades/export`
- `POST /reports/latest/download`

## FrontendViewController

Base path: `/api`

These APIs adapt backend or mock-like data for the Vue prototype:

- `GET /tasks`
- `GET /tasks/{taskId}`
- `GET /tasks/{taskId}/config-status`
- `GET /tasks/{taskId}/answers`
- `POST /tasks/{taskId}/answers/{versionId}/activate`
- `GET /rubrics`
- `GET /tasks/{taskId}/rubric-binding`
- `GET /export-templates`
- `GET /tasks/{taskId}/export-template`
- `GET /tasks/{taskId}/workspace`
- `POST /tasks/{taskId}/workspace/check`
- `POST /tasks/{taskId}/workspace/init`
- `POST /batch/start`
- `GET /batch/progress`
- `GET /batch/logs`
- `GET /students?taskId=...`
- `GET /students/{studentId}`
- `GET /analytics`
- `POST /batch/export`
- `GET /exports`

`/api/batch/*` remains a frontend prototype adapter path. Do not treat it as the real grading main flow; new backend work should target `/api/assessments/{id}/grading/*`.

## Frontend Client Mismatch Watch

`frontend-prototype/src/api/services.ts` defines additional client calls such as task-level answer upload, rubric create/update/delete/bind, export template create/update/bind. Verify backend implementation before relying on those calls in UI work.

The real standard-answer core path is now `/api/questions/{questionId}/standard-answers` and `/api/standard-answers/{id}`. `/api/tasks/{taskId}/answers` remains a frontend prototype adapter path and should not become the long-term write path.
