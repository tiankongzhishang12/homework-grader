# 后端最小阅卷闭环验收报告

生成日期：2026-05-08

## 任务范围

本报告检查当前后端从 `assessment` 到导出的最小 demo 主链路是否真实可用。报告已根据“评分结果入库适配器”实现更新；本次没有修改前端、数据库 SQL 表结构或 Python 脚本。

状态说明：

- `READY`：接口和数据链路基本可用。
- `PARTIAL`：接口存在，但数据链路或字段不完整。
- `SCRIPT_DEPENDENT`：依赖 Python 脚本产物，需准备 workspace 文件。
- `MISSING`：缺失。
- `MOCK_ONLY`：仅原型适配或 mock，不作为真实主线。

## 核心结论

当前后端最小阅卷 demo 的最大断点已经从“评分结果完全不入库”推进为“Python 评分产物可由 Java 后端导入 MySQL，但需要准备匹配的 workspace 和 submission 数据进行端到端验证”。

`POST /api/assessments/{id}/grading/start` 现在会在 `PythonScriptClient.runGrading()` 成功后调用 `GradingResultImportService.importScores(assessmentId)`，读取：

- `grader.workspace-root/student-mapping.csv`
- `grader.workspace-root/scores/*.json`

并尝试写入：

- `grading_run`
- `score_item_result`
- `final_result`

`GET /api/assessments/{id}/grading/progress` 仍使用内存 `Map` 保存进度，但返回中新增 `importSummary`，用于观察 `importedCount`、`skippedCount`、`failedCount` 以及对应明细。

## 最小 Demo 主链路检查表

| 步骤 | 当前接口/文件 | 状态 | 证据 | 风险 | 下一步 |
|---|---|---|---|---|---|
| 创建 assessment | `POST /api/assessments`；`AssessmentController.createAssessment`；`assessment` 表 | READY | Controller 调用 `CrudJdbcRepository.insert("assessment", request)`。 | 依赖请求体字段正确；业务校验较薄。 | demo 可先使用，后续补字段校验。 |
| 创建 assessment_template | `POST /api/assessments/{id}/templates`；`assessment_template` 表 | READY | Controller 写入 `assessment_id` 后插入 `assessment_template`。 | 未校验 assessment 是否存在；版本冲突依赖数据库约束。 | 后续补存在性校验。 |
| 创建 question_definition | `POST /api/templates/{id}/questions`；`question_definition` 表 | READY | Controller 写入 `template_id` 后插入 `question_definition`。 | 暂缺列表/更新接口。 | 后续补查询和配置校验。 |
| 创建 rubric_definition | `POST /api/templates/{id}/rubrics`；`rubric_definition` 表 | READY | Controller 写入 `template_id` 后插入 `rubric_definition`。 | 暂缺 Rubric 绑定和完整规则校验。 | 后续补版本和结构校验。 |
| 创建 standard_answer | `POST /api/questions/{questionId}/standard-answers`；`GET /api/questions/{questionId}/standard-answers`；`GET /api/standard-answers/{id}` | READY | `StandardAnswerService` 写入 `standard_answer.question_definition_id`，支持 `answer_text`/`answer_json` 和自动 `version_no`。 | 前端仍使用 `/api/tasks/{taskId}/answers` 原型路径。 | 前端后续改接 question 主线。 |
| 上传 submission | `POST /api/assessments/{id}/submissions/upload`；`SubmissionService.upload`；`submission` 表 | READY | Service 插入 `submission`，设置 `assessment_id`、`student_id`、`attempt_no`、`submit_status=UPLOADED`。 | Java 上传目录和 Python `raw` 学生目录仍需统一。 | 手动 demo 时要确保 workspace 输入和 submission 可匹配。 |
| 创建 submission_asset | `SubmissionService.upload`；`submission_asset` 表；`FileStorageService` | READY | 上传后保存文件并插入 `submission_asset`，包含路径、hash、大小、版本。 | Python 预处理脚本当前读取 workspace `raw` 下学生目录。 | 后续统一 Java 上传文件到 Python 输入目录的规则。 |
| 启动 grading | `POST /api/assessments/{id}/grading/start`；`GradingWorkflowService.start`；`PythonScriptClient` | SCRIPT_DEPENDENT | start 异步执行 Python 预处理和评分脚本，评分成功后调用 Java 入库适配器。 | 依赖 workspace 中存在脚本可处理的 raw/ir/scores 数据。 | 准备真实 workspace 样例后做端到端验证。 |
| 查询 grading progress | `GET /api/assessments/{id}/grading/progress` | PARTIAL | 返回 `assessmentId`、`status`、`message`、`scriptResult`、`importSummary`、`startedAt`、`updatedAt`。 | 进度仍是内存态，重启丢失。 | 后续迁移为数据库持久化或与 `grading_run` 映射。 |
| 创建 grading_run | `GradingResultImportService.insertGradingRun`；`grading_run` 表 | READY | 每个成功匹配的 score JSON 会为最新 submission 写入一条 `grading_run`。 | 需要 `student-mapping.csv`、`student.student_no`、`submission` 匹配成功。 | 手动验证入库数量和跳过明细。 |
| 创建 score_item_result | `GradingResultImportService.insertScoreItems`；`score_item_result` 表 | READY | 每个 `dimension_scores[]` 写一条 RUBRIC 分项结果，保留 evidence JSON、comment、confidence。 | 暂未映射 `rubric_definition_id` 和 `question_definition_id`。 | 后续增加 criterion/rubric code 到数据库定义的映射。 |
| 创建 final_result | `GradingResultImportService.upsertFinalResult`；`final_result` 表 | READY | 按 submission 唯一键插入或更新 `final_result`，选中刚创建的 `grading_run`。 | 若导入跳过，则对应学生仍没有 final_result。 | 通过 `importSummary.skipped` 定位数据准备问题。 |
| 查询 final_result | `GET /api/assessments/{id}/final-results` | READY | 当前导入成功后，接口可查到 assessment 下 submission 对应的 final_result。 | 需要真实导入成功；前端暂未接入。 | 使用手动 API 验证。 |
| confirm final_result | `PUT /api/final-results/{id}/confirm` | READY | `GradingWorkflowService.confirm` 写入 `review_status=CONFIRMED`、`confirmed_by_teacher_id`、`confirmed_at`。 | 仍依赖调用方传入有效 `teacher_id`。 | 后续接入前端教师复核。 |
| adjust final_result | `PUT /api/final-results/{id}/adjust` | PARTIAL | 可更新 `final_score`，设置 `score_source=TEACHER_ADJUSTED`、`review_status=ADJUSTED`。 | 暂未记录调整原因、调整人和时间。 | 后续补审计字段或调整记录。 |
| publish grades | `POST /api/assessments/{id}/grades/publish` | PARTIAL | Controller 插入 `grade_publish_record`。 | 未校验 final_result 是否已确认；未生成 `course_grade`。 | 联调前增加发布前校验和成绩汇总策略。 |
| export grades | `POST /api/assessments/{id}/grades/export`；`export_traceability_excel.py` | SCRIPT_DEPENDENT | 仍调 Python export script，从 workspace `scores` 生成 Excel。 | 导出不是直接基于 MySQL `final_result`；可能与当前 assessment 不一致。 | P1：导出改为基于 assessment 的 final_result 或明确同步策略。 |
| download latest report | `POST /api/reports/latest/download` | PARTIAL | 下载 reports 目录最新 `.xlsx`。 | 最新文件不一定属于当前 assessment。 | 增加 assessment/reportId 维度。 |

## Python 与数据库写入结论

### PythonScriptClient.runGrading() 后是否写入结果表

现在会由 Java 后端写入。`PythonScriptClient` 职责未变化，仍只负责执行 Python 脚本并返回 `ScriptResult`；写库逻辑由新增 `GradingResultImportService` 负责。

### 是 Java 写入还是 Python 写入

是 Java 写入。当前配置的 Python 脚本仍主要写 workspace 文件：

- `preprocess_student_dirs.py` 写 `ir/*.json` 和 `student-mapping.csv`。
- `batch_score_reports.py` 写 `scores/*.json` 和 `progress.json`。
- `export_traceability_excel.py` 读 `scores/*.json` 并写 `reports/*.xlsx`。

### workspace 文件导入数据库步骤

已新增。导入链路为：

`scores student_id -> student-mapping.csv anon_id -> student_number -> student.student_no -> student.id -> assessmentId + student.id 最新 submission -> grading_run/score_item_result/final_result`

如果找不到 mapping、student 或 submission，当前 score 文件会被跳过，批次继续处理其他文件，并在 `importSummary.skipped` 中记录原因。

### finalResults 接口数据能否由当前 grading/start 产生

可以，但前提是 Python 评分脚本成功生成 `scores/*.json`，且 `student-mapping.csv`、`student.student_no`、`submission` 能匹配。匹配成功后，`GET /api/assessments/{id}/final-results` 可以查到由本次导入生成或更新的 `final_result`。

### export 是否基于当前 assessment 的 final_result

仍不是。导出接口仍调 Python export script 并下载 workspace 最新 Excel，未改为从 MySQL `final_result` 按 assessment 导出。

## 原型适配接口定位

`FrontendViewController` 中 `/api/tasks/*` 和 `/api/batch/*` 仍属于前端原型适配层，不作为真实后端主流程验收依据。真实主线继续落在 `/api/assessments/*`、`/api/submissions/*`、`/api/assessments/{id}/grading/*`、`/api/grading-runs/*`、`/api/final-results/*`、`/api/assessments/{id}/grades/*`。

## 文档与代码冲突

- `.codex/skills/homework-grader-backend/references/backend-architecture.md` 仍写着 `confirm` 不设置 `confirmed_at`，当前代码已设置，该 reference 已过期。
- 本报告已修正此前关于“评分结果不入库”的结论：当前已由 Java 后端补齐导入适配器，但仍需要真实样例数据验证。
- 技术栈未发现新冲突；仍以 `backend/pom.xml` 的 Spring Boot 2.7.18 / Java 8 为准。

## 优先级建议

| 优先级 | 建议 | 原因 | 交付结果 |
|---|---|---|---|
| P0 | 用真实 workspace 和数据库样例跑通一次 `grading/start -> final-results`。 | 适配器已实现，但需要验证 mapping、student、submission 和 scores JSON 的真实匹配。 | `final-results` 能查到当前 assessment 的真实导入结果。 |
| P1 | 将导出改为基于当前 assessment 的 `final_result`，或建立明确的 DB 到 workspace export 同步策略。 | 现在导出仍依赖 workspace 最新 scores/Excel。 | 导出文件与当前 assessment 和最终成绩一致。 |
| P2 | 持久化 grading progress，并逐步降级 `/api/tasks/*`、`/api/batch/*` 原型接口。 | 进度内存态会重启丢失，双轨接口增加联调成本。 | 后端主线可恢复、可审计，前端逐步切换到真实接口。 |

## 手动验证建议

1. 准备 `workspace/practicum-batch/student-mapping.csv`，包含 `anon_id,student_number,name`。
2. 准备 `workspace/practicum-batch/scores/anon-001.json`，包含 `student_id`、`rubric_id`、`dimension_scores`、`raw_total_score`、`overall_confidence`、`review_flag`。
3. 确认数据库存在 `student.student_no = student_number`。
4. 确认该 `assessmentId` 下存在对应 `submission`。
5. 调用 `POST /api/assessments/{id}/grading/start`。
6. 调用 `GET /api/assessments/{id}/grading/progress`，检查 `importSummary`。
7. 调用 `GET /api/assessments/{id}/final-results`，检查是否出现 `final_result`。
## 2026-05-08 更新：评分结果入库完成判定

为避免“Python 脚本执行成功但没有任何评分结果入库”时误报完成，`GradingWorkflowService` 已强化完成判定：

- `failedCount > 0`：progress 状态为 `FAILED`，message 为 `Grading result import failed.`。
- `importedCount == 0`：progress 状态为 `FAILED`，message 为 `Grading script succeeded, but no grading results were imported.`。
- `importedCount > 0 && skippedCount > 0`：progress 状态为 `COMPLETED`，message 为 `Some grading results were imported; some were skipped.`。
- `importedCount > 0 && skippedCount == 0 && failedCount == 0`：progress 状态为 `COMPLETED`，message 为 `Grading completed and all results imported.`。

`progress` 中继续返回 `importSummary`，用于定位 mapping 缺失、student 缺失、submission 缺失或单文件导入异常。
## 2026-05-08 更新：自动验收脚本

已新增 `software-project-practicum/scripts/verify_backend_minimal_demo.py`，用于验证后端最小阅卷 demo：

- 默认 dry-run，不写数据库、不写 workspace、不调用后端业务接口。
- 只有传入 `--apply` 时，才写入或复用 `DEMO_*` 标识的本地测试数据。
- 脚本会准备 `student-mapping.csv` 和 `scores/anon-001.json`，调用 assessment 主线阅卷接口，检查 `final_result`、`score_item_result`，并调用 confirm 验证 `confirmed_at`。
- 脚本会生成 `docs/handoff/backend-minimal-demo-manual-test-record.md`。
- 脚本不删除真实数据，不清空表，不修改 schema，不修改 Python 评分脚本。

推荐 dry-run：

```bash
python software-project-practicum/scripts/verify_backend_minimal_demo.py --base-url http://localhost:8080 --workspace software-project-practicum/workspace/practicum-batch
```

真实验收必须显式追加 `--apply`，并确保本地后端、MySQL 和认证参数准备好。
