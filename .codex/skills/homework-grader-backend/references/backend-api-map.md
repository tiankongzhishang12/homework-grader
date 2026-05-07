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
- `GET /assessments/{id}/grading/progress`
- `GET /grading-runs/{id}`
- `GET /submissions/{id}/score-items`
- `GET /assessments/{id}/final-results`
- `PUT /final-results/{id}/confirm`
- `PUT /final-results/{id}/adjust`
- `POST /assessments/{id}/grades/publish`

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

## Frontend Client Mismatch Watch

`frontend-prototype/src/api/services.ts` defines additional client calls such as task-level answer upload, rubric create/update/delete/bind, export template create/update/bind. Verify backend implementation before relying on those calls in UI work.

The real standard-answer core path is now `/api/questions/{questionId}/standard-answers` and `/api/standard-answers/{id}`. `/api/tasks/{taskId}/answers` remains a frontend prototype adapter path and should not become the long-term write path.
