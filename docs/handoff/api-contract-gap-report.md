# 前后端 API 契约对齐报告

## 任务名

生成前后端 API 契约对齐报告

## 任务背景

当前项目是智能阅卷系统。前端位于 `software-project-practicum/frontend-prototype`，后端位于 `software-project-practicum/backend`。后端优先推进，前端已有 Vue 原型、Pinia stores、API client 和 mock server。为避免后续联调出现接口缺失、路径不一致、参数不一致和返回结构不一致，本报告对比前端 API client 与后端 Controller。

## 任务目标

- 扫描前端 `src/api/services.ts`，列出前端调用的接口路径、方法、函数和业务模块。
- 扫描后端 `controller/`，列出已实现接口路径、方法、Controller 和方法名。
- 分类已对齐接口、前端调用但后端缺失、后端已有但前端未使用、路径相似但方法/语义不一致、路径相同但参数或返回结构可能不一致。
- 按业务模块给出优先级和修复建议。

## 修改范围

本次只新增文档：

- `docs/handoff/api-contract-gap-report.md`

## 非目标

- 不修改业务代码。
- 不新增后端接口。
- 不删除前端 mock。
- 不修改数据库 SQL。
- 不移动 Python 脚本。
- 不做前端页面重构。
- 不做权限系统。

## 后端影响

本报告只读取后端 Controller 和相关 API 包，不改后端代码。后续修复会影响：

- `AuthController`
- `BaseDataController`
- `CourseController`
- `AssessmentController`
- `SubmissionController`
- `GradingController`
- `ExportController`
- `FrontendViewController`

## 前端影响

本报告只读取前端 API client、mock server、stores、views 和 router，不改前端代码。后续修复会影响：

- `src/api/services.ts`
- `src/api/client.ts`
- `src/api/mock-server.ts`
- `src/stores/config.ts`
- `src/stores/batch.ts`
- `src/stores/task-context.ts`
- `src/views/*`

## 数据库影响

无数据库变更。报告中涉及的数据事实来自后端 Controller 查询和现有数据库表语义。

## Python 脚本影响

无 Python 脚本变更。报告中涉及导出和批量阅卷时，仅指出后端仍通过 `PythonScriptClient` 调度脚本。

## 验收步骤

- 已读取 `AGENTS.md`。
- 已读取 Codex 指令模板。
- 已读取前端 API client、API request layer、mock server、stores/views 调用位置。
- 已读取后端 Controller。
- 已对照 `.codex/skills/homework-grader-backend/references/backend-api-map.md` 和前端 Skill references。

## 输出要求

完成后输出新增文件清单、前端 API 调用数量、后端接口数量、已对齐接口数量、缺失接口数量、契约不一致接口数量、P0 问题列表和后续建议。

## 统计摘要

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| 前端 API client 调用 | 33 | 统计自 `src/api/services.ts` 的 `apiRequest` 调用。 |
| 后端 Controller 接口 | 56 | 统计自当前 `controller/` 注解；包含通用后端接口、标准答案核心接口和 `FrontendViewController` 原型适配接口。 |
| 已对齐接口 | 23 | 路径和方法在前后端均存在。 |
| 前端调用但后端缺失 | 10 | 主要集中在标准答案上传/详情、Rubric 写操作、导出模板写操作。 |
| 后端已有但前端未使用 | 33 | 主要是组织人员、课程教学、考核任务、标准答案核心接口、学生提交、成绩确认发布和核心阅卷 API。 |
| 契约不一致或高风险接口 | 8 | 路径存在但仅支持 demo task、返回静态/聚合结构，或前端走原型接口而非核心后端流程。 |

## 前端 API 调用清单

| 模块 | 前端函数 | 方法 | 路径 |
| --- | --- | --- | --- |
| 登录认证 | `authApi.login` | POST | `/api/auth/login` |
| 登录认证 | `authApi.me` | GET | `/api/auth/me` |
| 登录认证 | `authApi.logout` | POST | `/api/auth/logout` |
| 考核任务 | `taskApi.list` | GET | `/api/tasks` |
| 考核任务 | `taskApi.get` | GET | `/api/tasks/{taskId}` |
| 考核任务 | `taskApi.blockers` | GET | `/api/tasks/{taskId}/config-status` |
| 标准答案 | `answerApi.list` | GET | `/api/tasks/{taskId}/answers` |
| 标准答案 | `answerApi.upload` | POST | `/api/tasks/{taskId}/answers` |
| 标准答案 | `answerApi.get` | GET | `/api/tasks/{taskId}/answers/{versionId}` |
| 标准答案 | `answerApi.activate` | POST | `/api/tasks/{taskId}/answers/{versionId}/activate` |
| Rubric | `rubricApi.list` | GET | `/api/rubrics` |
| Rubric | `rubricApi.binding` | GET | `/api/tasks/{taskId}/rubric-binding` |
| Rubric | `rubricApi.generate` | POST | `/api/rubrics/generate` |
| Rubric | `rubricApi.create` | POST | `/api/rubrics` |
| Rubric | `rubricApi.update` | PUT | `/api/rubrics/{rubricId}` |
| Rubric | `rubricApi.remove` | DELETE | `/api/rubrics/{rubricId}` |
| Rubric | `rubricApi.bind` | POST | `/api/tasks/{taskId}/rubric-binding` |
| 导出模板 | `exportTemplateApi.list` | GET | `/api/export-templates` |
| 导出模板 | `exportTemplateApi.current` | GET | `/api/tasks/{taskId}/export-template` |
| 导出模板 | `exportTemplateApi.create` | POST | `/api/export-templates` |
| 导出模板 | `exportTemplateApi.update` | PUT | `/api/export-templates/{templateId}` |
| 导出模板 | `exportTemplateApi.bind` | POST | `/api/tasks/{taskId}/export-template/bind` |
| 考核任务 | `workspaceApi.get` | GET | `/api/tasks/{taskId}/workspace` |
| 考核任务 | `workspaceApi.check` | POST | `/api/tasks/{taskId}/workspace/check` |
| 考核任务 | `workspaceApi.init` | POST | `/api/tasks/{taskId}/workspace/init` |
| 批量阅卷 | `batchApi.start` | POST | `/api/batch/start` |
| 批量阅卷 | `batchApi.progress` | GET | `/api/batch/progress?taskId={taskId}` |
| 批量阅卷 | `batchApi.logs` | GET | `/api/batch/logs?taskId={taskId}` |
| 结果分析 | `resultApi.students` | GET | `/api/students?taskId={taskId}` |
| 学生详情 | `resultApi.student` | GET | `/api/students/{studentId}?taskId={taskId}` |
| 结果分析 | `resultApi.analytics` | GET | `/api/analytics?taskId={taskId}` |
| 导出 | `exportApi.start` | POST | `/api/batch/export` |
| 导出 | `exportApi.history` | GET | `/api/exports?taskId={taskId}` |

## 后端接口清单

| 模块 | Controller | 方法名 | 方法 | 路径 |
| --- | --- | --- | --- | --- |
| 登录认证 | `AuthController` | `login` | POST | `/api/auth/login` |
| 登录认证 | `AuthController` | `me` | GET | `/api/auth/me` |
| 登录认证 | `AuthController` | `logout` | POST | `/api/auth/logout` |
| 组织人员 | `BaseDataController` | `orgTree` | GET | `/api/org/tree` |
| 组织人员 | `BaseDataController` | `teachers` | GET | `/api/teachers` |
| 组织人员 | `BaseDataController` | `createTeacher` | POST | `/api/teachers` |
| 组织人员 | `BaseDataController` | `students` | GET | `/api/students` |
| 组织人员 | `BaseDataController` | `importStudent` | POST | `/api/students/import` |
| 课程教学 | `CourseController` | `courses` | GET | `/api/courses` |
| 课程教学 | `CourseController` | `createCourse` | POST | `/api/courses` |
| 课程教学 | `CourseController` | `courseOfferings` | GET | `/api/course-offerings` |
| 课程教学 | `CourseController` | `createCourseOffering` | POST | `/api/course-offerings` |
| 课程教学 | `CourseController` | `teachingClassStudents` | GET | `/api/teaching-classes/{id}/students` |
| 考核任务 | `AssessmentController` | `assessments` | GET | `/api/assessments` |
| 考核任务 | `AssessmentController` | `createAssessment` | POST | `/api/assessments` |
| 考核任务 | `AssessmentController` | `assessment` | GET | `/api/assessments/{id}` |
| 考核任务 | `AssessmentController` | `createTemplate` | POST | `/api/assessments/{id}/templates` |
| 考核任务 | `AssessmentController` | `createQuestion` | POST | `/api/templates/{id}/questions` |
| Rubric | `AssessmentController` | `createRubric` | POST | `/api/templates/{id}/rubrics` |
| 标准答案 | `StandardAnswerController` | `create` | POST | `/api/questions/{questionId}/standard-answers` |
| 标准答案 | `StandardAnswerController` | `listByQuestion` | GET | `/api/questions/{questionId}/standard-answers` |
| 标准答案 | `StandardAnswerController` | `get` | GET | `/api/standard-answers/{id}` |
| 学生提交 | `SubmissionController` | `upload` | POST | `/api/assessments/{id}/submissions/upload` |
| 学生提交 | `SubmissionController` | `submissions` | GET | `/api/assessments/{id}/submissions` |
| 学生提交 | `SubmissionController` | `submission` | GET | `/api/submissions/{id}` |
| 学生提交 | `SubmissionController` | `download` | GET | `/api/submissions/{id}/assets/{assetId}/download` |
| 批量阅卷 | `GradingController` | `start` | POST | `/api/assessments/{id}/grading/start` |
| 批量阅卷 | `GradingController` | `progress` | GET | `/api/assessments/{id}/grading/progress` |
| 批量阅卷 | `GradingController` | `gradingRun` | GET | `/api/grading-runs/{id}` |
| 学生详情 | `GradingController` | `scoreItems` | GET | `/api/submissions/{id}/score-items` |
| 成绩确认与发布 | `GradingController` | `finalResults` | GET | `/api/assessments/{id}/final-results` |
| 成绩确认与发布 | `GradingController` | `confirm` | PUT | `/api/final-results/{id}/confirm` |
| 成绩确认与发布 | `GradingController` | `adjust` | PUT | `/api/final-results/{id}/adjust` |
| 成绩确认与发布 | `GradingController` | `publish` | POST | `/api/assessments/{id}/grades/publish` |
| 导出 | `ExportController` | `export` | POST | `/api/assessments/{id}/grades/export` |
| 导出 | `ExportController` | `latestReport` | POST | `/api/reports/latest/download` |
| 考核任务 | `FrontendViewController` | `tasks` | GET | `/api/tasks` |
| 考核任务 | `FrontendViewController` | `task` | GET | `/api/tasks/{taskId}` |
| 考核任务 | `FrontendViewController` | `configStatus` | GET | `/api/tasks/{taskId}/config-status` |
| 标准答案 | `FrontendViewController` | `answers` | GET | `/api/tasks/{taskId}/answers` |
| 标准答案 | `FrontendViewController` | `activateAnswer` | POST | `/api/tasks/{taskId}/answers/{versionId}/activate` |
| Rubric | `FrontendViewController` | `rubrics` | GET | `/api/rubrics` |
| Rubric | `FrontendViewController` | `rubricBinding` | GET | `/api/tasks/{taskId}/rubric-binding` |
| 导出模板 | `FrontendViewController` | `exportTemplates` | GET | `/api/export-templates` |
| 导出模板 | `FrontendViewController` | `currentExportTemplate` | GET | `/api/tasks/{taskId}/export-template` |
| 考核任务 | `FrontendViewController` | `workspace` | GET | `/api/tasks/{taskId}/workspace` |
| 考核任务 | `FrontendViewController` | `checkWorkspace` | POST | `/api/tasks/{taskId}/workspace/check` |
| 考核任务 | `FrontendViewController` | `initWorkspace` | POST | `/api/tasks/{taskId}/workspace/init` |
| 批量阅卷 | `FrontendViewController` | `startBatch` | POST | `/api/batch/start` |
| 批量阅卷 | `FrontendViewController` | `batchProgress` | GET | `/api/batch/progress?taskId=...` |
| 批量阅卷 | `FrontendViewController` | `batchLogs` | GET | `/api/batch/logs?taskId=...` |
| 结果分析 | `FrontendViewController` | `students` | GET | `/api/students?taskId=...` |
| 学生详情 | `FrontendViewController` | `student` | GET | `/api/students/{studentId}?taskId=...` |
| 结果分析 | `FrontendViewController` | `analytics` | GET | `/api/analytics?taskId=...` |
| 导出 | `FrontendViewController` | `export` | POST | `/api/batch/export` |
| 导出 | `FrontendViewController` | `exports` | GET | `/api/exports?taskId=...` |

## 已对齐接口

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 登录认证 | POST | `/api/auth/login` | 前端登录与后端 session 登录一致。 |
| 登录认证 | GET | `/api/auth/me` | 前端恢复登录态与后端当前用户一致。 |
| 登录认证 | POST | `/api/auth/logout` | 前端登出与后端 session invalidate 一致。 |
| 考核任务 | GET | `/api/tasks` | 前端任务列表有后端原型适配接口。 |
| 考核任务 | GET | `/api/tasks/{taskId}` | 有后端原型适配接口，但见契约风险。 |
| 考核任务 | GET | `/api/tasks/{taskId}/config-status` | 有后端原型适配接口，但见契约风险。 |
| 标准答案 | GET | `/api/tasks/{taskId}/answers` | 有后端原型适配接口。 |
| 标准答案 | POST | `/api/tasks/{taskId}/answers/{versionId}/activate` | 有后端原型适配接口。 |
| Rubric | GET | `/api/rubrics` | 有后端原型适配接口。 |
| Rubric | GET | `/api/tasks/{taskId}/rubric-binding` | 有后端原型适配接口。 |
| 导出模板 | GET | `/api/export-templates` | 有后端原型适配接口。 |
| 导出模板 | GET | `/api/tasks/{taskId}/export-template` | 有后端原型适配接口。 |
| 考核任务 | GET | `/api/tasks/{taskId}/workspace` | 有后端原型适配接口。 |
| 考核任务 | POST | `/api/tasks/{taskId}/workspace/check` | 有后端原型适配接口。 |
| 考核任务 | POST | `/api/tasks/{taskId}/workspace/init` | 有后端原型适配接口。 |
| 批量阅卷 | POST | `/api/batch/start` | 有后端原型适配接口。 |
| 批量阅卷 | GET | `/api/batch/progress?taskId=...` | 有后端原型适配接口。 |
| 批量阅卷 | GET | `/api/batch/logs?taskId=...` | 有后端原型适配接口。 |
| 结果分析 | GET | `/api/students?taskId=...` | 有后端原型适配接口；与基础学生列表同路径但通过 params 区分。 |
| 学生详情 | GET | `/api/students/{studentId}?taskId=...` | 有后端原型适配接口。 |
| 结果分析 | GET | `/api/analytics?taskId=...` | 有后端原型适配接口。 |
| 导出 | POST | `/api/batch/export` | 有后端原型适配接口。 |
| 导出 | GET | `/api/exports?taskId=...` | 有后端原型适配接口。 |

## 前端调用但后端缺失

| 优先级 | 模块 | 前端函数 | 方法 | 路径 | 建议 |
| --- | --- | --- | --- | --- | --- |
| P0 | 标准答案 | `answerApi.upload` | POST | `/api/tasks/{taskId}/answers` | 标准答案真实核心接口已补齐为 `/api/questions/{questionId}/standard-answers`；当前前端 task-level 上传路径仍未接入真实主线，不应继续扩展为长期写路径。 |
| P1 | 标准答案 | `answerApi.get` | GET | `/api/tasks/{taskId}/answers/{versionId}` | 详情页/版本查看需要后端返回单个标准答案版本。 |
| P1 | Rubric | `rubricApi.generate` | POST | `/api/rubrics/generate` | 前端 Rubric 生成依赖 mock；后端未实现模型生成或草稿接口。 |
| P1 | Rubric | `rubricApi.create` | POST | `/api/rubrics` | 前端创建的是 `Rubric` 聚合对象；后端当前只有 `/api/templates/{id}/rubrics` 写 `rubric_definition`。 |
| P1 | Rubric | `rubricApi.update` | PUT | `/api/rubrics/{rubricId}` | 前端支持更新 Rubric，后端缺失。 |
| P2 | Rubric | `rubricApi.remove` | DELETE | `/api/rubrics/{rubricId}` | 前端支持删除草稿 Rubric，后端缺失。 |
| P1 | Rubric | `rubricApi.bind` | POST | `/api/tasks/{taskId}/rubric-binding` | 前端支持任务绑定 Rubric，后端仅支持读取绑定。 |
| P1 | 导出模板 | `exportTemplateApi.create` | POST | `/api/export-templates` | 前端支持新建导出模板，后端仅支持读取静态模板。 |
| P1 | 导出模板 | `exportTemplateApi.update` | PUT | `/api/export-templates/{templateId}` | 前端支持编辑导出模板，后端缺失。 |
| P1 | 导出模板 | `exportTemplateApi.bind` | POST | `/api/tasks/{taskId}/export-template/bind` | 前端支持绑定任务导出模板，后端缺失。 |

## 后端已有但前端未使用

| 优先级 | 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- | --- |
| P2 | 组织人员 | GET | `/api/org/tree` | 前端当前没有组织树 API client。 |
| P2 | 组织人员 | GET | `/api/teachers` | 前端当前没有教师列表 API client。 |
| P2 | 组织人员 | POST | `/api/teachers` | 前端当前没有教师创建 API client。 |
| P2 | 组织人员 | GET | `/api/students` | 前端使用 `/api/students?taskId=...` 作为结果列表；基础学生列表未接入。 |
| P2 | 组织人员 | POST | `/api/students/import` | 前端没有学生导入 API client。 |
| P2 | 课程教学 | GET | `/api/courses` | 前端没有课程基础数据 API client。 |
| P2 | 课程教学 | POST | `/api/courses` | 前端没有课程创建 API client。 |
| P2 | 课程教学 | GET | `/api/course-offerings` | 前端没有开课实例 API client。 |
| P2 | 课程教学 | POST | `/api/course-offerings` | 前端没有开课创建 API client。 |
| P2 | 课程教学 | GET | `/api/teaching-classes/{id}/students` | 前端没有教学班学生 API client。 |
| P1 | 考核任务 | GET | `/api/assessments` | 前端当前使用 `/api/tasks` 原型聚合接口，未直接接入真实考核任务。 |
| P1 | 考核任务 | POST | `/api/assessments` | 前端没有创建考核任务 API client。 |
| P1 | 考核任务 | GET | `/api/assessments/{id}` | 前端没有真实 assessment 详情 API client。 |
| P1 | 考核任务 | POST | `/api/assessments/{id}/templates` | 前端没有 assessment template 创建 API client。 |
| P1 | 考核任务 | POST | `/api/templates/{id}/questions` | 前端没有题目定义 API client。 |
| P1 | Rubric | POST | `/api/templates/{id}/rubrics` | 前端使用 `/api/rubrics` 聚合路径，不使用模板下 rubric_definition 写入路径。 |
| P1 | 标准答案 | POST | `/api/questions/{questionId}/standard-answers` | 后端已提供真实标准答案创建接口，前端仍使用 `/api/tasks/{taskId}/answers` 原型路径。 |
| P1 | 标准答案 | GET | `/api/questions/{questionId}/standard-answers` | 后端已提供按 question_definition 查询标准答案列表，前端尚未接入。 |
| P1 | 标准答案 | GET | `/api/standard-answers/{id}` | 后端已提供单个 standard_answer 查询接口，前端尚未接入。 |
| P1 | 学生提交 | POST | `/api/assessments/{id}/submissions/upload` | 前端没有学生提交上传 API client；配置页的标准答案上传不是同一业务。 |
| P1 | 学生提交 | GET | `/api/assessments/{id}/submissions` | 前端没有真实提交列表 API client。 |
| P1 | 学生提交 | GET | `/api/submissions/{id}` | 前端没有提交详情 API client。 |
| P1 | 学生提交 | GET | `/api/submissions/{id}/assets/{assetId}/download` | 前端没有原始提交/资产下载 API client。 |
| P0 | 批量阅卷 | POST | `/api/assessments/{id}/grading/start` | 后端真实主线接口已稳定返回 `assessmentId`、`status`、`message`、`scriptResult`、`startedAt`、`updatedAt`；前端仍使用 `/api/batch/start`。 |
| P0 | 批量阅卷 | GET | `/api/assessments/{id}/grading/progress` | 后端真实主线接口已稳定同形状进度返回；当前进度仍为内存态，后续应迁移数据库持久化；前端仍使用 `/api/batch/progress?taskId=...`。 |
| P1 | 批量阅卷 | GET | `/api/grading-runs/{id}` | 前端没有评分运行详情 API client。 |
| P1 | 学生详情 | GET | `/api/submissions/{id}/score-items` | 前端使用聚合的学生详情接口，未直接读取 score item。 |
| P0 | 成绩确认与发布 | GET | `/api/assessments/{id}/final-results` | 前端没有最终成绩列表 API client，影响教师复核闭环。 |
| P0 | 成绩确认与发布 | PUT | `/api/final-results/{id}/confirm` | 后端确认接口已写入 `review_status`、`confirmed_by_teacher_id`、`confirmed_at`；前端没有成绩确认 API client，影响联调闭环。 |
| P0 | 成绩确认与发布 | PUT | `/api/final-results/{id}/adjust` | 前端没有成绩调整 API client，影响教师复核闭环。 |
| P0 | 成绩确认与发布 | POST | `/api/assessments/{id}/grades/publish` | 前端没有成绩发布 API client。 |
| P0 | 导出 | POST | `/api/assessments/{id}/grades/export` | 前端使用 `/api/batch/export` 原型导出，未接入核心导出脚本接口。 |
| P1 | 导出 | POST | `/api/reports/latest/download` | 前端没有最新报表下载 API client；方法为 POST，需要与下载交互约定。 |

## 路径相似但请求方法或语义不一致

| 优先级 | 模块 | 前端契约 | 后端已有相似契约 | 问题 |
| --- | --- | --- | --- | --- |
| P0 | 批量阅卷 | `POST /api/batch/start` with `{ taskId }` | `POST /api/assessments/{id}/grading/start` | 前端 taskId 与后端 assessment id 未建立映射，真实阅卷主流程会分叉。 |
| P0 | 批量阅卷 | `GET /api/batch/progress?taskId=...` | `GET /api/assessments/{id}/grading/progress` | 进度查询路径和 id 语义不一致。 |
| P0 | 导出 | `POST /api/batch/export` with `{ taskId }` | `POST /api/assessments/{id}/grades/export` | 前端导出是原型记录，后端核心导出会调度 Python export script。 |
| P1 | Rubric | `POST /api/rubrics` | `POST /api/templates/{id}/rubrics` | 前端按 Rubric 聚合对象创建，后端按 template 下的 rubric_definition 创建。 |
| P1 | 学生提交 | 无前端真实提交上传 | `POST /api/assessments/{id}/submissions/upload?studentId=...` | 前端配置页上传标准答案，后端上传接口是学生提交，二者不可混用。 |
| P1 | 导出下载 | 无前端下载 client | `POST /api/reports/latest/download` | 下载接口使用 POST，前端导出中心目前只维护历史记录，不下载真实文件。 |

当前未发现“完全相同路径但前后端请求方法不同”的接口。主要问题是相似业务使用了两套路由和 id 语义。

## 路径相同但参数或返回结构可能不一致

| 优先级 | 模块 | 方法 | 路径 | 风险 |
| --- | --- | --- | --- | --- |
| P1 | 考核任务 | GET | `/api/tasks` | 后端 `FrontendViewController` 当前查询标题为“答题卡评分联调测试”的种子数据，并映射为固定 demo task；前端 mock 有多个 task。 |
| P1 | 考核任务 | GET | `/api/tasks/{taskId}` | 后端仅接受 `answer-card-demo`，前端路由和 mock 支持任意 taskId。 |
| P2 | 考核任务 | GET | `/api/tasks/{taskId}/config-status` | 后端当前总是返回空 blockers，前端期望反映标准答案、Rubric、导出模板、workspace 的配置缺口。 |
| P1 | 标准答案 | GET | `/api/tasks/{taskId}/answers` | 后端返回固定标准答案版本，前端 store 还支持上传、解析中、解析失败、草稿和激活状态。 |
| P1 | 批量阅卷 | POST | `/api/batch/start` | 后端只支持 demo task，并使用内存状态；前端期望任务配置通过后启动批量流程。 |
| P1 | 批量阅卷 | GET | `/api/batch/progress?taskId=...` | 后端返回固定 completed 聚合结果；前端 `BatchProgress` 支持 preprocessing/grading/exporting/failed 等过程状态。 |
| P1 | 结果分析 | GET | `/api/students?taskId=...` | 后端通过 `params=taskId` 与 `BaseDataController` 的基础 `/api/students` 区分；前端需要明确始终带 taskId。 |
| P1 | 导出 | POST | `/api/batch/export` | 后端原型接口返回模拟 `ExportRecord`，不等同 `ExportController` 的 Python 导出和最新 xlsx 下载。 |

## 按业务模块差距与优先级

### 登录认证

- 已对齐：`login`、`me`、`logout`。
- 风险：前端 `client.ts` 默认 `VITE_USE_MOCK_API !== "false"`，默认走 mock；真实联调必须设置 `VITE_USE_MOCK_API=false`。
- 优先级：P1。

### 组织人员

- 后端已有组织树、教师、学生基础数据接口。
- 前端 API client 未覆盖组织树、教师、基础学生导入。
- 优先级：P2，除非下一阶段要做基础数据维护页面。

### 课程教学

- 后端已有课程、开课、教学班学生接口。
- 前端当前通过 `/api/tasks` 使用聚合后的课程任务视图，未接入课程教学基础接口。
- 优先级：P2。

### 考核任务

- 前端使用 `/api/tasks` 原型任务视图。
- 后端真实考核接口为 `/api/assessments` 系列。
- P0/P1 风险：taskId 与 assessment id 的映射需要明确，否则批量阅卷、提交、最终成绩和导出无法接入同一条主流程。

### 标准答案

- 原型适配已有：`GET /api/tasks/{taskId}/answers`、`POST /api/tasks/{taskId}/answers/{versionId}/activate`。
- 真实核心接口已补齐：`POST /api/questions/{questionId}/standard-answers`、`GET /api/questions/{questionId}/standard-answers`、`GET /api/standard-answers/{id}`。
- 仍需前端联调：前端 `answerApi.upload` 仍指向 `/api/tasks/{taskId}/answers`，需要在后续改为 question/template/assessment 主线。

### Rubric

- 已有：列表、读取绑定。
- 缺失：生成、创建、更新、删除、绑定。
- P1：会阻塞 Rubric 管理页面联调。

### 导出模板

- 已有：列表、读取当前模板。
- 缺失：创建、更新、绑定。
- P1：会阻塞导出模板配置联调。

### 学生提交

- 后端已有真实提交上传、列表、详情、资产下载。
- 前端 API client 未接入。
- P1：若下一阶段要支持教师上传/导入学生提交，需要补前端 client 和页面入口。

### 批量阅卷

- 前端使用 `/api/batch/*` 原型接口。
- 后端核心接口是 `/api/assessments/{id}/grading/*`，并已稳定 start/progress 返回字段：`assessmentId`、`status`、`message`、`scriptResult`、`startedAt`、`updatedAt`。
- 当前 progress 仍由 `GradingWorkflowService` 内存 Map 保存，后续需要迁移为数据库持久化。
- P0 剩余问题：前端尚未从 `/api/batch/*` 切换到 assessment 主线，且 taskId/assessmentId 映射仍需统一。

### 结果分析

- 前端 `students` 和 `analytics` 已有原型适配接口。
- 风险：后端当前基于 demo seed 聚合，未覆盖通用 assessment。
- P1：联调真实任务时需要泛化。

### 学生详情

- 前端已有 `/api/students/{studentId}?taskId=...` 原型接口。
- 后端核心 score item 接口 `/api/submissions/{id}/score-items` 未被前端直接使用。
- P1：需要决定保留聚合详情接口，还是让前端组合 submission/final result/score items。

### 成绩确认与发布

- 后端已有 final results、confirm、adjust、publish。
- `confirm` 已写入 `review_status = CONFIRMED`、`confirmed_by_teacher_id` 和 `confirmed_at`。
- 前端完全没有对应 API client。
- P0 剩余问题：前端尚未接入“教师复核 -> 最终成绩确认/调整 -> 发布”的可审计闭环。

### 导出

- 前端导出走 `/api/batch/export` 和 `/api/exports`。
- 后端核心导出走 `/api/assessments/{id}/grades/export` 和 `/api/reports/latest/download`。
- P0：导出链路未接入真实 Python 导出脚本和 xlsx 下载。

## Mock 依赖位置与替换建议

| 位置 | 当前依赖 | 替换建议 |
| --- | --- | --- |
| `src/api/client.ts` | `USE_MOCK = import.meta.env.VITE_USE_MOCK_API !== "false"`，默认启用 mock。 | 联调环境必须设置 `VITE_USE_MOCK_API=false`，并配置 `VITE_API_BASE_URL`。 |
| `src/api/mock-server.ts` | 实现了前端全部 33 个 client 调用，包括后端缺失的写操作。 | 将缺失接口按 P0/P1 补齐后，逐步把 store 调用切到真实后端。 |
| `src/stores/config.ts` | 标准答案上传、Rubric 生成/创建/绑定/删除、导出模板创建/绑定依赖 mock 才完整可用。 | 优先补标准答案上传、Rubric 绑定、导出模板绑定契约。 |
| `src/stores/batch.ts` | 批量开始、进度、日志、结果、导出均可由 mock 完整模拟。 | 将 `/api/batch/*` 与 `/api/assessments/{id}/grading/*` 做映射或统一。 |
| `src/views/AssignmentDetailView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/CourseTasksView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/DashboardView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/ScoringRulesView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/StudentListView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/TaskCenterView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |
| `src/views/TeachingClassesView.vue` | 直接从 `mock-data` 导入。 | 未入当前 router，可后置处理。 |

## 文档与代码冲突

- 未发现 README 或根目录 `SKILL.md` 中存在 Spring Boot 3 / Java 17 与当前 `pom.xml` 冲突的问题；当前代码与 README 均指向 Spring Boot `2.7.18`、Java 8。
- `.codex/skills/homework-grader-backend/references/backend-api-map.md` 已记录 “Frontend Client Mismatch Watch”，与本次代码扫描一致。
- 新发现的契约事实：前端 mock server 已实现若干写接口，但真实后端 Controller 未实现。这不是文档冲突，而是前后端实现差距。

## P0 问题列表

| 编号 | 问题 | 影响 | 建议 |
| --- | --- | --- | --- |
| P0-1 | 标准答案真实核心接口已补齐，但前端 `POST /api/tasks/{taskId}/answers` 仍未接入真实主线。 | 后端已可按 question_definition 维护 `standard_answer`，但前端配置页仍需迁移。 | 后续将前端标准答案写入改为 `/api/questions/{questionId}/standard-answers`，并明确 taskId 到 assessment/template/question 的映射。 |
| P0-2 | 后端 `/api/assessments/{id}/grading/start` 和 `/progress` 已稳定真实返回结构，但前端仍使用 `/api/batch/*`。 | 后端小闭环已可脱离 `/api/batch/*`；前端联调仍无法验证真实 `GradingWorkflowService` 和 `PythonScriptClient` 主流程。 | Phase 2 在前端 service 增加 assessment grading API，并建立 taskId/assessmentId 映射；当前 progress 内存态后续迁移为数据库持久化。 |
| P0-3 | 后端 `confirm` 已写入 `confirmed_at`，但前端未使用 `final_result` 确认、调整、发布接口。 | 后端审计字段已补强；教师复核、最终成绩确认和发布仍无法在前端完成联调。 | 增加 `finalResultApi` / `gradePublishApi`，在学生详情或结果列表接入 confirm/adjust/publish。 |
| P0-4 | 前端导出使用 `/api/batch/export` 原型接口，未接入 `/api/assessments/{id}/grades/export` 和 `/api/reports/latest/download`。 | 导出中心无法触发真实 Python 导出脚本，也无法下载最新 xlsx 报表。 | 将导出中心接入核心导出接口，并补下载 API client。 |

## 后续建议

1. 先统一任务 id 语义：决定前端 `taskId` 是否直接等于后端 `assessment.id`，或提供映射字段。
2. 优先补 P0：前端接入核心阅卷启动/进度、final result confirm/adjust/publish、真实导出和下载。
3. 第二阶段补 P1：Rubric 写操作、导出模板写操作、真实提交列表/详情/资产下载。
4. 保留 `FrontendViewController` 作为短期适配层时，需明确它只服务 demo 任务还是要泛化为生产聚合 API。
5. 联调前在前端环境中设置 `VITE_USE_MOCK_API=false`，否则所有差距会被 mock server 掩盖。
# 2026-05-08 更新：后端评分结果入库链路

后端 assessment 主线已新增 `GradingResultImportService`：

- `POST /api/assessments/{id}/grading/start` 在 Python grading 脚本成功后，会读取 `grader.workspace-root/scores/*.json` 和 `student-mapping.csv`。
- Java 后端会按 `anon_id -> student_number -> student.student_no -> submission` 映射写入 `grading_run`、`score_item_result`、`final_result`。
- `GET /api/assessments/{id}/grading/progress` 返回结构新增 `importSummary`，用于记录 imported / skipped / failed。
- `GET /api/assessments/{id}/final-results` 现在可以查询由评分 JSON 导入生成的最终结果，前提是 student mapping、student 和 submission 均能匹配。
- 前端仍未接入 assessment 主线，仍使用 `/api/batch/*` 和 `/api/tasks/*` 原型适配接口；本次不修改前端。
