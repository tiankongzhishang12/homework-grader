# 后端主流程 API 统一方案

## 任务名

设计后端主流程 API 统一方案

## 任务背景

`docs/handoff/api-contract-gap-report.md` 已指出当前前端原型接口与后端真实业务接口存在 P0 缺口，尤其是：

- `/api/batch/*` 与 `/api/assessments/{id}/grading/*` 阅卷流程不一致；
- `final_result` 确认、调整、发布接口已有后端实现但未进入前端主流程；
- 导出仍走 `/api/batch/export` 原型接口，未接入真实 `/api/assessments/{id}/grades/export` 和 `/api/reports/latest/download`；
- 标准答案上传接口缺失，任务配置闭环不完整。

当前开发策略是单人开发，先做好后端主流程，再做前端联调，暂不做复杂权限系统。本方案用于统一后端 API 主线，避免后续继续维护两套任务语义。

## 任务目标

- 明确当前存在两套路由体系。
- 明确以 `assessment` 作为后端核心任务实体。
- 明确 `taskId` 与 `assessmentId` 的关系。
- 设计后端主流程接口顺序。
- 给每个 P0 缺口制定修复策略。
- 给出 Phase 1 到 Phase 4 的分阶段计划。
- 给出 P0/P1/P2 优先级表。

## 修改范围

本次只新增文档：

- `docs/handoff/backend-main-flow-api-unification-plan.md`

## 非目标

- 不修改后端代码。
- 不修改前端代码。
- 不修改 SQL 表结构。
- 不删除 `/api/tasks/*` 原型接口。
- 不删除 `/api/batch/*` 原型接口。
- 不做权限系统。

## 后端影响

后续实现会主要影响：

- `AssessmentController`
- `SubmissionController`
- `GradingController`
- `ExportController`
- `FrontendViewController`
- `GradingWorkflowService`
- `SubmissionService`
- `CrudJdbcRepository`

当前 `PythonScriptClient` 和 `grader.python.*` 是主流程的一部分，不迁移、不删除。

## 前端影响

本方案不改前端代码。后续 Phase 2 会要求前端 API client 从原型接口迁移到后端核心接口，尤其是：

- 阅卷启动和进度；
- final result 确认、调整、发布；
- 真实导出和下载；
- 标准答案上传；
- taskId/assessmentId 映射。

## 数据库影响

本方案不修改 SQL 表结构。后端主流程应基于现有表：

- `assessment`
- `assessment_template`
- `question_definition`
- `rubric_definition`
- `standard_answer`
- `submission`
- `submission_asset`
- `extraction_run`
- `extraction_result`
- `grading_run`
- `score_item_result`
- `final_result`
- `course_grade`
- `grade_publish_record`

组织、教师、学生、课程和教学班来自：

- `organization_unit`
- `teacher`
- `student`
- `course`
- `course_offering`
- `teaching_class`
- `course_offering_teacher`
- `teaching_class_student`

## Python 脚本影响

无 Python 脚本变更。后续后端实现仍应保留：

- `PythonScriptClient.runPreprocess()`
- `PythonScriptClient.runGrading()`
- `PythonScriptClient.runExport()`
- `grader.python.preprocess-script`
- `grader.python.grading-script`
- `grader.python.export-script`

## 验收步骤

本次文档任务已核对：

- `AGENTS.md`
- 根目录 `SKILL.md`
- `docs/handoff/api-contract-gap-report.md`
- backend Skill references
- grading workflow Skill references
- 后端 Controller、Service、Repository
- `database/grading_schema_v2.sql`
- `database/organization_schema_v2.sql`

## 输出要求

完成后输出新增文件清单、核心结论、推荐优先修复的第一个后端任务、是否发现文档与代码冲突。

## 当前两套路由体系

### 前端原型聚合接口

当前 Vue 原型主要依赖 `FrontendViewController` 提供的聚合接口：

- `/api/tasks`
- `/api/tasks/{taskId}`
- `/api/tasks/{taskId}/config-status`
- `/api/tasks/{taskId}/answers`
- `/api/tasks/{taskId}/answers/{versionId}/activate`
- `/api/tasks/{taskId}/rubric-binding`
- `/api/tasks/{taskId}/export-template`
- `/api/tasks/{taskId}/workspace`
- `/api/tasks/{taskId}/workspace/check`
- `/api/tasks/{taskId}/workspace/init`
- `/api/batch/start`
- `/api/batch/progress`
- `/api/batch/logs`
- `/api/batch/export`
- `/api/exports`
- `/api/analytics`
- `/api/students?taskId=...`
- `/api/students/{studentId}?taskId=...`

这些接口适合前端原型演示和聚合展示，但当前实现明显带有 demo 适配特征：

- `FrontendViewController` 使用固定 `DEMO_TASK_ID = "answer-card-demo"`；
- task 数据来自特定演示 assessment 标题；
- `/api/batch/*` 返回前端期望的演示进度和日志，不等同真实 `GradingWorkflowService` 主流程；
- `/api/batch/export` 返回模拟 `ExportRecord`，不调度真实导出脚本。

### 后端核心业务接口

后端真实业务主线已经分布在多个 Controller：

- `/api/assessments/*`
- `/api/templates/*`
- `/api/assessments/{id}/submissions/*`
- `/api/submissions/*`
- `/api/assessments/{id}/grading/*`
- `/api/grading-runs/*`
- `/api/submissions/{id}/score-items`
- `/api/assessments/{id}/final-results`
- `/api/final-results/*`
- `/api/assessments/{id}/grades/publish`
- `/api/assessments/{id}/grades/export`
- `/api/reports/latest/download`

这些接口更接近数据库领域模型，也更适合作为后端主流程的 source of truth。

## 核心结论

后续应以后端核心业务接口作为主线：

- `assessment` 是后端核心任务实体。
- `assessment.id` 是后端主流程的任务主键。
- 如果前端继续使用 `taskId`，它应当只是展示层 ID 或 `assessmentId` 的别名。
- 不建议长期保留 `taskId` 与 `assessmentId` 两套语义。
- `/api/tasks/*` 和 `/api/batch/*` 暂时保留，不删除，但定位为前端原型适配层。
- 真实配置、提交、阅卷、复核、发布、导出必须最终落到 `/api/assessments/*`、`/api/submissions/*`、`/api/grading-runs/*`、`/api/final-results/*` 主线。

推荐的短期统一策略：

1. 后端新增或补齐核心接口，不急着删除原型接口。
2. 前端联调时让 `taskId = String(assessment.id)`，把原型 task 视图中的 `id` 字段改成真实 assessment id 的字符串。
3. `/api/tasks/*` 可以作为读取聚合视图的兼容层，但不能再承载写入、阅卷、确认、发布、导出等主流程动作。
4. `/api/batch/*` 仅保留为旧前端原型兼容，后续可转发到 `/api/assessments/{id}/grading/*` 或在 Phase 3 降级为 deprecated。

## 主键语义设计

| 名称 | 建议语义 | 长期状态 |
| --- | --- | --- |
| `assessment.id` | 后端核心任务主键，连接 template、submission、grading、final result、publish、export。 | 保留，作为主线。 |
| `assessmentId` | API path 和前端真实 API client 使用的参数名。 | 保留，推荐。 |
| `taskId` | 前端展示层任务 ID；短期可等于 `String(assessment.id)`；也可由 `/api/tasks` 聚合接口返回。 | 不建议作为独立业务主键长期存在。 |
| `DEMO_TASK_ID` | 当前 `FrontendViewController` 演示任务 ID。 | Phase 3 降级或移除依赖。 |

决策：从后端主流程角度，任何写入类动作都应使用 `assessmentId` 或其下级实体 id，不再新增依赖独立 `taskId` 的写接口。

## 后端主流程接口顺序

### 1. 创建 assessment

当前已有：

- `POST /api/assessments`
- Controller：`AssessmentController.createAssessment`
- 写入表：`assessment`

建议主线：

- 请求必须包含 `course_offering_id`、`title`、`assessment_type`、`submission_format`、`grading_mode`、`total_score` 等 schema 必填字段。
- 返回至少包含新建 `assessment.id`。
- 前端后续把 `taskId` 设置为该 `assessment.id` 的字符串。

### 2. 创建 template

当前已有：

- `POST /api/assessments/{id}/templates`
- Controller：`AssessmentController.createTemplate`
- 写入表：`assessment_template`

建议主线：

- `{id}` 是 `assessmentId`。
- 返回 `templateId`，供后续题目、Rubric、标准答案绑定。

### 3. 创建 question_definition

当前已有：

- `POST /api/templates/{id}/questions`
- Controller：`AssessmentController.createQuestion`
- 写入表：`question_definition`

建议主线：

- `{id}` 是 `templateId`。
- 每个题目或题型区块都应有明确 `question_no`、`question_type`、`max_score`、`sort_order`。

### 4. 创建 rubric_definition

当前已有：

- `POST /api/templates/{id}/rubrics`
- Controller：`AssessmentController.createRubric`
- 写入表：`rubric_definition`

建议主线：

- `{id}` 是 `templateId`。
- 不建议短期以 `/api/rubrics` 作为写入主线，因为现有 schema 中 Rubric 从属于 `assessment_template`。
- 前端 Rubric 聚合对象可在 Phase 2 适配为多个 `rubric_definition`。

### 5. 创建或导入 standard_answer

当前状态：

- schema 有 `standard_answer`。
- `CrudJdbcRepository` allowlist 有 `standard_answer`。
- 后端已补齐按 `question_definition` 维护 `standard_answer` 的真实核心接口。

当前核心接口：

- `POST /api/questions/{questionId}/standard-answers`
- `GET /api/questions/{questionId}/standard-answers`
- `GET /api/standard-answers/{id}`

后续如果需要文件上传解析，可增加：

- `POST /api/templates/{templateId}/standard-answers/import`

建议不要把真实写入主线放在 `/api/tasks/{taskId}/answers`，该路径可作为前端原型兼容层。

### 6. 上传 submission

当前已有：

- `POST /api/assessments/{id}/submissions/upload`
- Controller：`SubmissionController.upload`
- Service：`SubmissionService.upload`
- 写入表：`submission`、`submission_asset`
- 文件存储：`FileStorageService`

建议主线：

- `{id}` 是 `assessmentId`。
- `studentId` 当前是 request param。
- `file` 是 multipart 文件。
- 后续可补批量导入，但主线先稳定单个上传。

### 7. 启动 grading

当前已有：

- `POST /api/assessments/{id}/grading/start`
- Controller：`GradingController.start`
- Service：`GradingWorkflowService.start`
- 调度：`PythonScriptClient.runPreprocess()`、`PythonScriptClient.runGrading()`

建议主线：

- `{id}` 是 `assessmentId`。
- 返回标准化进度对象，至少包含 `assessmentId`、`status`、`message`、`scriptResult` 或 run summary。
- 暂时不做复杂权限。

### 8. 查询 grading progress

当前已有：

- `GET /api/assessments/{id}/grading/progress`
- Controller：`GradingController.progress`

建议主线：

- 保持当前路径。
- 后续可把内存进度落库到 `grading_run` 或新增状态记录，但本方案不改 schema。
- `/api/batch/progress?taskId=...` 不作为主线。

### 9. 查询 score_item_result

当前已有：

- `GET /api/submissions/{id}/score-items`
- Controller：`GradingController.scoreItems`
- 查询表：`score_item_result` join `grading_run`

建议主线：

- `{id}` 是 `submissionId`。
- 用于学生详情页展示分项得分、证据、置信度、复核标记和评语。

### 10. 查询 final_result

当前已有：

- `GET /api/assessments/{id}/final-results`
- Controller：`GradingController.finalResults`
- 查询表：`final_result` join `submission`

建议主线：

- `{id}` 是 `assessmentId`。
- 作为结果列表、教师复核队列和导出前确认的数据源。

### 11. confirm / adjust final_result

当前已有：

- `PUT /api/final-results/{id}/confirm`
- `PUT /api/final-results/{id}/adjust`
- Controller：`GradingController.confirm`、`GradingController.adjust`
- Service：`GradingWorkflowService.confirm`、`GradingWorkflowService.adjust`

建议主线：

- `{id}` 是 `finalResultId`。
- `confirm` 请求体当前需要 `teacher_id`。
- `adjust` 请求体当前可包含 `final_score`。
- 后续实现建议补 `confirmed_at`，并考虑调整原因字段；不改 schema 时可先在现有可用字段范围内做最小闭环。

### 12. publish grades

当前已有：

- `POST /api/assessments/{id}/grades/publish`
- Controller：`GradingController.publish`
- 写入表：`grade_publish_record`

建议主线：

- `{id}` 是 `assessmentId`。
- 请求体应包含 `published_by_teacher_id`、`published_at`，后端补默认 `publish_scope` 和 `publish_status`。
- 发布前应确认 final results 已经可审计。

### 13. export grades

当前已有：

- `POST /api/assessments/{id}/grades/export`
- Controller：`ExportController.export`
- 调度：`PythonScriptClient.runExport()`
- 输出：最新 `.xlsx` 报表文件名。

建议主线：

- `{id}` 是 `assessmentId`。
- 返回应明确 `assessmentId`、script result、report file name。
- `/api/batch/export` 不作为真实导出主线。

### 14. download latest report

当前已有：

- `POST /api/reports/latest/download`
- Controller：`ExportController.latestReport`
- 返回：`FileSystemResource`

建议主线：

- 短期保留当前 POST。
- 前端下载时要按文件流处理，不要按 JSON envelope 处理。
- 后续可考虑增加 `GET /api/reports/latest/download`，但不是 Phase 1 必须项。

## P0 缺口修复策略

### P0-1 标准答案上传

现状：

- 前端调用 `POST /api/tasks/{taskId}/answers`。
- 后端已补齐真实核心接口 `/api/questions/{questionId}/standard-answers` 和 `/api/standard-answers/{id}`。
- 数据库已有 `standard_answer`，且它通过 `question_definition_id` 关联题目。
- `/api/tasks/{taskId}/answers` 仍是前端原型适配接口，不应继续作为真实主线写路径。

策略：

1. 不把 `/api/tasks/{taskId}/answers` 作为真实写入主线。
2. 后端标准答案核心接口已经围绕 `questionId` 补齐：
   - `POST /api/questions/{questionId}/standard-answers`
   - `GET /api/questions/{questionId}/standard-answers`
   - `GET /api/standard-answers/{id}`
3. 可选后续能力：`POST /api/templates/{templateId}/standard-answers/import`
4. 若前端短期仍使用 taskId，则 Phase 2 在前端或适配层把 `taskId -> assessmentId -> active templateId -> questionId` 映射清楚。

推荐第一个后端任务：

- 补齐标准答案最小 CRUD：先支持按 `question_definition_id` 写入 `standard_answer.answer_text` 或 `answer_json`，并返回版本信息。

### P0-2 `/api/batch/*` 与 `/api/assessments/*` 对齐

现状：

- 前端 `POST /api/batch/start` 使用 `{ taskId }`。
- 后端核心 `POST /api/assessments/{id}/grading/start` 使用 `assessmentId`。
- `FrontendViewController` 的 `/api/batch/*` 是 demo 聚合接口。

策略：

1. 后端主线保持 `/api/assessments/{id}/grading/start` 和 `/api/assessments/{id}/grading/progress`。
2. Phase 1 不删除 `/api/batch/*`。
3. Phase 2 前端改为调用 assessment grading API。
4. Phase 3 如需兼容旧前端，可让 `/api/batch/start` 内部只做参数转换并转发到核心 service，但标注 deprecated。

### P0-3 `final_result` 前端接入

现状：

- 后端已有：
  - `GET /api/assessments/{id}/final-results`
  - `PUT /api/final-results/{id}/confirm`
  - `PUT /api/final-results/{id}/adjust`
  - `POST /api/assessments/{id}/grades/publish`
- 前端 API client 没有这些接口。

策略：

1. 后端主线保留当前接口。
2. Phase 1 后端补强返回结构和审计字段可用性，尤其是 `confirmed_at`。
3. Phase 2 前端新增 `finalResultApi` 和 `gradePublishApi`。
4. 教师复核 UI 应围绕 `final_result`，不要只展示 mock 的学生详情分数。

### P0-4 导出接口对齐

现状：

- 前端导出：`POST /api/batch/export`、`GET /api/exports?taskId=...`。
- 后端真实导出：`POST /api/assessments/{id}/grades/export`、`POST /api/reports/latest/download`。
- 真实导出会调度 `PythonScriptClient.runExport()`。

策略：

1. 后端主线保持 assessment export。
2. Phase 1 稳定导出返回结构，确保返回 report file name 和 script result。
3. Phase 2 前端导出中心改调真实导出接口，并用文件流下载最新报表。
4. Phase 3 `/api/batch/export` 降级为 demo 或 deprecated。

## 分阶段计划

### Phase 1：后端核心接口补齐与稳定

目标：让后端在不依赖前端原型接口的情况下跑通配置、提交、阅卷、复核、发布、导出主流程。

建议任务：

1. 标准答案核心接口已补齐；下一步稳定其联调用例和错误返回。
2. 稳定 assessment/template/question/rubric 创建顺序和返回结构。
3. 稳定 submission 上传与 asset 下载。
4. 稳定 `/api/assessments/{id}/grading/start` 和 progress 返回结构。
5. 确认 `final_result` 查询、确认、调整、发布接口可用，并尽量补齐 `confirmed_at`。
6. 稳定真实导出和 latest report 下载。

验收：

- 使用 assessment id 可以完成从配置到导出的主流程。
- 不需要 `/api/tasks/*` 或 `/api/batch/*` 才能完成后端闭环。

### Phase 2：前端 API client 改为真实接口

目标：让前端联调真实后端主流程。

建议任务：

1. 在前端 API client 中新增 assessment/template/question/standardAnswer/submission/grading/finalResult/export API。
2. 让 `taskId` 短期等于 `String(assessment.id)`。
3. 将批量阅卷按钮从 `/api/batch/start` 改为 `/api/assessments/{assessmentId}/grading/start`。
4. 将结果列表和学生详情逐步改为 final results、submissions、score items 的聚合。
5. 将导出中心改为真实 export 和 latest report download。

验收：

- `VITE_USE_MOCK_API=false` 时，教师可完成主流程联调。

### Phase 3：清理或降级 `/api/tasks/*`、`/api/batch/*` 原型接口

目标：减少双轨接口维护成本。

建议任务：

1. 保留 `/api/tasks` 作为只读聚合视图，或替换为 assessment list 聚合结果。
2. 将 `/api/batch/*` 标注为 deprecated。
3. 如必须保留兼容，则 `/api/batch/*` 内部转发到 assessment grading/export 主线。
4. 移除 demo-only 假设，例如固定 `DEMO_TASK_ID`。

验收：

- 主流程没有任何必须依赖 demo task 的步骤。

### Phase 4：再做基础权限

目标：在主流程稳定后再加权限，不提前引入复杂角色系统。

建议任务：

1. 保持当前 session 登录。
2. 先做教师身份与 `teacher_id` 的基本关联。
3. 再限制 assessment、course offering、final result 的可见范围。
4. 发布、确认、调整操作必须记录教师身份。

验收：

- 不破坏 Phase 1 到 Phase 3 的主流程。

## 优先级表

| 优先级 | 任务 | 推荐阶段 | 说明 |
| --- | --- | --- | --- |
| P0 | 补标准答案核心接口 | Phase 1 | 已补齐真实核心接口；后续需前端迁移和联调。 |
| P0 | 统一阅卷启动和进度主线到 `/api/assessments/{id}/grading/*` | Phase 1 | 阻塞后端主流程闭环。 |
| P0 | 稳定 final results 查询、confirm、adjust、publish | Phase 1 | 阻塞教师复核和可审计成绩闭环。 |
| P0 | 稳定 assessment export 和 latest report download | Phase 1 | 阻塞真实导出闭环。 |
| P1 | 前端新增真实 assessment/grading/finalResult/export API client | Phase 2 | 阻塞前后端联调。 |
| P1 | 将 `taskId` 映射为 `assessmentId` | Phase 2 | 阻塞路由语义统一。 |
| P1 | Rubric 写操作与 template rubric_definition 对齐 | Phase 2 | 阻塞 Rubric 管理联调。 |
| P1 | 导出模板创建、更新、绑定接口对齐 | Phase 2 | 阻塞导出模板配置联调。 |
| P1 | 学生提交列表、详情、资产下载接入前端 | Phase 2 | 阻塞真实提交管理联调。 |
| P2 | `/api/tasks/*` 泛化为只读聚合视图 | Phase 3 | 降低 demo-only 风险。 |
| P2 | `/api/batch/*` 标注 deprecated 或内部转发 | Phase 3 | 降低双轨维护成本。 |
| P2 | 基础权限和教师范围控制 | Phase 4 | 主流程稳定后再做。 |

## 不建议的做法

- 不建议继续在 `/api/tasks/{taskId}/answers` 上扩展真实写入主流程。
- 不建议让 `/api/batch/*` 成为真实阅卷主线。
- 不建议在未统一 taskId/assessmentId 前做前端大规模联调。
- 不建议为了匹配前端 mock 而绕开现有 `assessment`、`submission`、`grading_run`、`final_result` 数据链路。
- 不建议删除 `FrontendViewController`，但应降低它对主流程的影响。

## 文档与代码冲突

本次未发现 README、根目录 `SKILL.md` 或 Skill references 与代码存在新的技术栈冲突。当前代码事实仍是：

- 后端核心任务实体：`assessment`
- 当前真实阅卷接口：`/api/assessments/{id}/grading/start` 和 `/api/assessments/{id}/grading/progress`
- 当前原型适配接口：`/api/tasks/*` 和 `/api/batch/*`
- 当前导出脚本调度：`ExportController` -> `PythonScriptClient.runExport()`

需要记录的实现差距：

- `standard_answer` 表存在，但后端缺少真实核心标准答案创建/上传/详情接口。
- `final_result.confirm` 当前更新 `review_status` 和 `confirmed_by_teacher_id`，未设置 `confirmed_at`。
- `/api/reports/latest/download` 当前使用 POST 返回文件流，前端联调时需要特殊处理。

## 推荐优先修复的第一个后端任务

“标准答案核心接口补齐”已完成，下一步优先做后端主流程阅卷接口稳定。

理由：

- 标准答案接口已经可以串起 `assessment_template -> question_definition -> standard_answer -> grading`。
- 当前下一个后端 P0 是稳定 `/api/assessments/{id}/grading/start` 与 `/api/assessments/{id}/grading/progress` 的真实返回结构。
- 这样可以让后端在不依赖 `/api/batch/*` 的情况下跑通真实阅卷主流程。

建议第一个任务范围：

- 规范 grading start/progress 返回结构
- 保持使用 `GradingWorkflowService`
- 保持 `PythonScriptClient` 和 `grader.python.*`
- 不改 SQL schema
- 不动 Python 脚本
