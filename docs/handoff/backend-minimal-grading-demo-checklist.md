# 后端最小阅卷闭环验收报告

生成日期：2026-05-08

## 任务范围

本报告只检查当前后端从 `assessment` 到导出的最小 demo 主链路是否真实可用，不修改业务代码、前端代码、数据库 SQL 或 Python 脚本。

判定状态：

- `READY`：接口和数据链路基本可用。
- `PARTIAL`：接口存在，但数据链路或字段不完整。
- `SCRIPT_DEPENDENT`：依赖 Python 脚本产物，需额外验证脚本写库或文件产物。
- `MISSING`：缺失。
- `MOCK_ONLY`：仅原型适配或 mock，不应作为真实主线。

## 核心结论

当前后端还不能真实跑通 “创建任务配置 -> 上传提交 -> 自动评分 -> 生成最终成绩 -> 教师确认 -> 发布 -> 导出” 的完整最小闭环。

已经可用的部分包括：任务和模板基础创建、题目和 Rubric 定义创建、标准答案创建、提交上传、`submission_asset` 创建、阅卷启动和内存进度查询、已有 `final_result` 的查询/确认/调整、发布记录插入、调度导出脚本并下载最新 Excel。

最大断点在评分结果落库：`POST /api/assessments/{id}/grading/start` 调用 `PythonScriptClient.runPreprocess()` 和 `PythonScriptClient.runGrading()` 后，只把脚本结果写入内存进度 `Map`，未把评分结果写入 `grading_run`、`score_item_result`、`final_result`。当前配置的 Python 脚本主要把 IR、评分 JSON、进度 JSON 和 Excel 写到 workspace 文件系统，未发现 MySQL 写库逻辑；后端也未发现从 workspace JSON 导入数据库结果表的步骤。

因此，`GET /api/assessments/{id}/final-results` 可以查询已有数据库记录，但这些记录不能由当前 `grading/start` 流程自动产生。

## 最小 Demo 主链路检查表

| 步骤 | 当前接口/文件 | 状态 | 证据 | 风险 | 下一步 |
|---|---|---|---|---|---|
| 创建 assessment | `POST /api/assessments`；`AssessmentController.createAssessment`；`assessment` 表 | READY | Controller 直接调用 `CrudJdbcRepository.insert("assessment", request)`。 | 依赖请求体字段正确；目前没有业务级校验。 | demo 可先使用，后续补字段校验和默认值。 |
| 创建 assessment_template | `POST /api/assessments/{id}/templates`；`assessment_template` 表 | READY | Controller 写入 `assessment_id` 后插入 `assessment_template`。 | 没有校验 assessment 是否存在；版本冲突依赖数据库约束。 | demo 可先使用，后续补存在性校验。 |
| 创建 question_definition | `POST /api/templates/{id}/questions`；`question_definition` 表 | READY | Controller 写入 `template_id` 后插入 `question_definition`。 | 暂缺列表/更新接口；题目结构由调用方直接传字段。 | demo 可先创建，后续补查询和配置校验。 |
| 创建 rubric_definition | `POST /api/templates/{id}/rubrics`；`rubric_definition` 表 | READY | Controller 写入 `template_id` 后插入 `rubric_definition`。 | 暂缺 Rubric 绑定、版本管理和完整规则校验。 | demo 可先创建，后续补版本和结构校验。 |
| 创建 standard_answer | `POST /api/questions/{questionId}/standard-answers`；`GET /api/questions/{questionId}/standard-answers`；`GET /api/standard-answers/{id}` | READY | `StandardAnswerService` 写入 `standard_answer.question_definition_id`，支持 `answer_text`/`answer_json` 和自动 `version_no`。 | 前端仍使用 `/api/tasks/{taskId}/answers` 原型路径。 | 后端主线已可用；前端后续改接 question 主线。 |
| 上传 submission | `POST /api/assessments/{id}/submissions/upload`；`SubmissionService.upload`；`submission` 表 | READY | Service 插入 `submission`，设置 `assessment_id`、`student_id`、`attempt_no`、`submit_status=UPLOADED`。 | 没有与 Python workspace raw 目录建立自动同步。 | demo 可上传文件；后续明确 Java 上传文件与 Python 输入目录的关系。 |
| 创建 submission_asset | `SubmissionService.upload`；`submission_asset` 表；`FileStorageService` | READY | 上传后保存文件并插入 `submission_asset`，包含路径、hash、大小、版本。 | Python 预处理脚本当前读取 workspace raw 学生目录，不一定读取 Java 上传目录。 | P0 任务中统一 submission_asset 到 Python 输入或 Java 导入链路。 |
| 启动 grading | `POST /api/assessments/{id}/grading/start`；`GradingWorkflowService.start`；`PythonScriptClient.runPreprocess/runGrading` | SCRIPT_DEPENDENT | start 进入 `QUEUED` 后异步执行 Python 预处理和评分脚本。 | 脚本输入来自 `grader.workspace-root`，不保证包含当前 assessment 的上传文件；评分结果未落库。 | 实现 assessment 级评分输入准备和结果持久化。 |
| 查询 grading progress | `GET /api/assessments/{id}/grading/progress`；`GradingWorkflowService.progress` | PARTIAL | 返回 `assessmentId`、`status`、`message`、`scriptResult`、`startedAt`、`updatedAt`；找不到任务返回 `IDLE`。 | 进度只在内存 `Map`，重启丢失；不反映数据库 `grading_run` 状态。 | 后续迁移为数据库持久化或与 `grading_run` 建立映射。 |
| 是否创建 grading_run | `grading_run` 表；`CrudJdbcRepository` allowlist | MISSING | Java 代码中未发现 `repository.insert("grading_run", ...)`；`runGrading()` 只返回脚本结果。 | 没有评分运行记录，后续分项结果和最终结果缺少审计根。 | P0：在评分流程中创建并更新 `grading_run`。 |
| 是否创建 score_item_result | `score_item_result` 表；`GET /api/submissions/{id}/score-items` | MISSING | 查询接口存在，但当前 `grading/start` 未创建 `score_item_result`；Python 脚本输出 scores JSON，未发现 DB 写入。 | 分项得分、证据、置信度无法从真实流程进入数据库。 | P0：把脚本评分 JSON 映射写入 `score_item_result`。 |
| 是否创建 final_result | `final_result` 表；`GET /api/assessments/{id}/final-results` | MISSING | 查询接口存在，但当前 `grading/start` 未创建 `final_result`。 | 教师确认、调整、发布和导出缺少真实上游数据。 | P0：按 submission 聚合生成 `final_result`。 |
| 查询 final_result | `GET /api/assessments/{id}/final-results` | PARTIAL | Controller 通过 `final_result join submission` 按 `assessment_id` 查询。 | 只能查已有或手工/种子数据；不能由当前评分流程自动产生。 | 结果落库后再作为真实主线查询接口。 |
| confirm final_result | `PUT /api/final-results/{id}/confirm`；`GradingWorkflowService.confirm` | PARTIAL | 已写入 `review_status=CONFIRMED`、`confirmed_by_teacher_id`、`confirmed_at`。 | 依赖已有 `final_result`；当前评分流程不会生成该记录。 | 保留现有行为；等待上游 `final_result` 自动生成。 |
| adjust final_result | `PUT /api/final-results/{id}/adjust`；`GradingWorkflowService.adjust` | PARTIAL | 可更新 `final_score`，设置 `score_source=TEACHER_ADJUSTED`、`review_status=ADJUSTED`。 | 依赖已有 `final_result`；暂未记录调整原因、调整人和时间。 | demo 可先用于已有结果；后续补审计字段或调整记录。 |
| publish grades | `POST /api/assessments/{id}/grades/publish`；`grade_publish_record` 表 | PARTIAL | Controller 插入 `grade_publish_record`，默认 `publish_scope=ASSESSMENT`、`publish_status=PUBLISHED`。 | 没有校验 final_result 是否已确认；没有生成或更新 `course_grade`。 | 联调前增加发布前校验和成绩汇总策略。 |
| export grades | `POST /api/assessments/{id}/grades/export`；`PythonScriptClient.runExport`；`export_traceability_excel.py` | SCRIPT_DEPENDENT | ExportController 调用 Python export script；脚本从 workspace `scores` 读取 JSON 并写 Excel。 | 导出不按 assessmentId 过滤数据库 `final_result`；若 workspace scores 不是当前 assessment，会导出错集。 | P1：导出改为基于 assessment 的 `final_result`，或明确从 DB 生成导出源。 |
| download latest report | `POST /api/reports/latest/download`；`FileStorageService.reportsRoot()` | PARTIAL | 后端选择 reports 目录最新 `.xlsx` 下载。 | 最新文件不等于当前 assessment 报表；接口使用 POST 下载也需前端适配。 | P1：增加 assessment/reportId 维度，避免下载错报表。 |

## Python 与数据库写入结论

### PythonScriptClient.runGrading() 后是否写入结果表

没有发现 Java 代码在 `PythonScriptClient.runGrading()` 后写入 `grading_run`、`score_item_result` 或 `final_result`。

证据：

- `GradingWorkflowService.runWorkflow` 只调用 `runPreprocess()`、`runGrading()` 并更新内存 `progress`。
- `PythonScriptClient` 只用 `ProcessBuilder` 执行脚本，并返回 `ScriptResult(script, startedAt, finishedAt, exitCode, stdout, stderr)`。
- `CrudJdbcRepository` allowlist 包含结果表，但当前评分 workflow 没有调用这些表的 insert。

### 如果写入，是 Java 写入还是 Python 写入

当前未发现写入。既不是 Java 写入，也未在当前配置脚本中发现 Python 写 MySQL。

证据：

- `software-project-practicum/scripts/preprocess_student_dirs.py` 写入 workspace `ir/*.json` 和 `student-mapping.csv`。
- `software-project-practicum/scripts/batch_score_reports.py` 写入 workspace `scores/*.json` 和 `progress.json`。
- `software-project-practicum/scripts/export_traceability_excel.py` 从 workspace `scores` 读取 JSON，写入 workspace `reports/*.xlsx`。
- 对 `software-project-practicum/scripts/` 和根目录 `scripts/` 搜索 `pymysql`、`sqlalchemy`、`INSERT`、`grading_run`、`score_item_result`、`final_result`，未发现评分脚本直接写业务数据库的路径。

### 是否有 workspace 文件导入数据库步骤

未发现。当前后端没有从 workspace `scores/*.json` 导入 `grading_run`、`score_item_result`、`final_result` 的 Service 或 Controller。

### finalResults 接口数据能否由当前 grading/start 产生

不能。`GET /api/assessments/{id}/final-results` 查询 `final_result join submission`，但当前 `grading/start` 不创建 `final_result`。

### export 是否基于当前 assessment 的 final_result

不是。`POST /api/assessments/{id}/grades/export` 接收 assessmentId 并返回它，但实际执行的 `export_traceability_excel.py` 从 workspace `scores` 目录读取 JSON，`ExportController` 再选择 reports 目录最新 `.xlsx`。当前未发现按 assessmentId 查询 `final_result` 后导出的逻辑。

## 原型适配接口定位

`FrontendViewController` 中 `/api/tasks/*` 和 `/api/batch/*` 仍属于前端原型适配层，包含固定 `DEMO_TASK_ID = answer-card-demo`、内存 `batchStarted` 状态、固定进度和模拟导出记录。它们可以支撑前端原型展示，但不应作为真实后端主流程验收依据。

真实主线应继续落在：

- `/api/assessments/*`
- `/api/submissions/*`
- `/api/assessments/{id}/grading/*`
- `/api/grading-runs/*`
- `/api/final-results/*`
- `/api/assessments/{id}/grades/*`
- `/api/reports/latest/download`

## 文档与代码冲突

- `docs/handoff/backend-main-flow-api-unification-plan.md` 末尾“需要记录的实现差距”仍写着 `standard_answer` 表存在但后端缺少真实核心标准答案创建/上传/详情接口；当前代码已经有 `StandardAnswerController` 和 `StandardAnswerService`，该条已过期。
- 同一文档中“后端闭环”相关描述需要按本报告收窄：`start/progress` 小闭环已可脱离 `/api/batch/*`，但完整 `assessment -> final_result -> export` 闭环尚未真实打通。
- 技术栈未发现新的冲突；仍以 `backend/pom.xml` 的 Spring Boot 2.7.18 / Java 8 为准。

## 优先级建议

| 优先级 | 建议 | 原因 | 交付结果 |
|---|---|---|---|
| P0 | 实现评分结果持久化导入任务：在 `GradingWorkflowService` 的评分成功后，把当前 assessment/submission 对应的脚本结果或 demo 评分结果写入 `grading_run`、`score_item_result`、`final_result`。 | 没有这一步，教师确认、发布和导出都没有真实上游数据，demo 跑不通。 | 调用 `grading/start` 后，`final-results` 能查到当前 assessment 的结果。 |
| P1 | 将导出改为基于当前 assessment 的 `final_result`，并让下载接口支持 assessment/reportId 定位。 | 现在导出的是 workspace 最新 scores/Excel，不保证属于当前 assessment。 | 导出文件与当前 assessment、最终成绩、教师确认状态一致。 |
| P2 | 持久化 grading progress，并逐步降级 `/api/tasks/*`、`/api/batch/*` 原型接口。 | 进度内存态会重启丢失，双轨接口会增加联调成本。 | 后端主线可恢复、可审计，前端逐步切换到真实接口。 |

## 推荐下一个 Codex 代码任务

任务名建议：`实现 grading/start 后评分结果入库`

目标：保持 `PythonScriptClient` 职责不变，在 Java 后端新增一个结果导入/持久化 Service。评分脚本成功后，读取 workspace `scores/*.json` 或一个明确的 assessment 结果文件，按当前 `assessment_id` 和 `submission` 映射写入：

- `grading_run`
- `score_item_result`
- `final_result`

同时应记录失败原因、置信度、模型输出摘要、证据 JSON 和运行状态，确保后续 `final_result.confirm`、发布和导出有可审计的数据来源。
