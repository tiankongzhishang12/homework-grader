# Codex Project Rules: Homework Grader

## 项目定位

本仓库是智能阅卷系统 `tiankongzhishang12/homework-grader`。系统面向课程作业、软件项目实训报告、考试答题卡和类似教学评价场景，目标是支撑可配置、可追踪、可复核、可导出的智能阅卷流程。

当前项目使用 ChatGPT / OpenAI-compatible 模型、Codex 协作开发能力、Spring Boot 后端、Vue 前端、MySQL 数据库和 Python 辅助脚本。根目录 `SKILL.md` 是 Codex Project Context，不是旧助手平台 Skill 安装说明。

## 主要目录

- `README.md`：项目入口说明，保留现有内容。
- `SKILL.md`：Codex 项目上下文，不要改回旧平台 Skill。
- `AGENTS.md`：本文件，定义 Codex 在本仓库内协作时必须遵守的项目级规则。
- `.codex/skills/`：按任务触发的 Agent Skills，详细资料放在各 Skill 的 `references/` 中。
- `database/`：MySQL 建库、组织结构、阅卷业务表和数据模型资料。
- `software-project-practicum/backend/`：Spring Boot 后端。
- `software-project-practicum/frontend-prototype/`：Vue 前端原型。
- `software-project-practicum/scripts/`：当前实训报告批处理、评分和导出脚本。
- `software-project-practicum/answer-card/`：答题卡识别、标准构建、验证评分和导出资料。
- `scripts/`、`templates/`、`examples/`、`references/`：通用评分、Rubric、Prompt、模板、示例和质量控制资料。

## 文档与代码冲突

技术栈、接口、配置、路由、表结构以当前代码为准。发现 README、根目录 `SKILL.md`、`.codex/skills/**/references/` 或其他文档与代码冲突时，必须在输出中报告冲突，不要悄悄按文档猜测实现。

当前已确认 `software-project-practicum/backend/pom.xml` 使用 Spring Boot `2.7.18` 和 Java `1.8`。如果其他文档写 Spring Boot 3 或 Java 17，以 `pom.xml` 为准并报告冲突。

## 后端规则

- 修改后端前先检查 `backend/pom.xml`、`application.yml`、`controller/`、`service/`、`repository/`、`client/python/`、`storage/` 和 `config/`。
- 保持 Spring Boot 2.7.x / Java 8 兼容性，除非用户明确要求升级。
- 当前数据访问使用 `CrudJdbcRepository`、`JdbcTemplate` 和 `NamedParameterJdbcTemplate`，不要无计划引入 ORM 重构。
- 不要删除 `PythonScriptClient` 和 `grader.python.*` 配置，除非用户明确要求迁移为纯 Java 或其他调度方式。
- 涉及登录态、CORS、拦截器、文件上传、导出下载时，必须同时检查前端 API 调用和浏览器行为。

## 前端规则

- 前端位于 `software-project-practicum/frontend-prototype/`，当前使用 Vue 3、TypeScript、Vite、Vue Router 和 Pinia。
- 前端是教师工作台，不做营销页。首屏应直接服务任务、配置、阅卷、分析、学生详情或导出工作。
- 修改路由时以 `src/router.ts` 为准，同时检查 `src/api/services.ts`、Pinia stores 和相关 views。
- 涉及成绩、置信度、复核状态、导出状态时，界面必须让教师看清数据来源、状态和可执行动作。

## 数据库规则

- 当前数据库 SQL 位于 `database/organization_schema_v2.sql` 和 `database/grading_schema_v2.sql`。
- 不要修改数据库 SQL 的实际表结构，除非用户明确要求 schema 变更。
- 任何 schema 变更都必须说明影响的后端字段、前端展示、Python 脚本、历史数据和回滚方案。
- 涉及成绩、评分、教师复核、导出时，必须保留可追踪和可审计能力，包括运行记录、分项证据、最终结果、教师确认和发布记录。

## 智能阅卷业务规则

- Rubric、标准答案、题目定义、抽取结果、评分运行、分项评分、最终成绩和导出记录是一个连续链路，不要只改其中一环。
- 模型输出不能直接等同最终成绩。最终成绩应经过系统规则聚合，并支持教师确认或调整。
- 低置信度、异常分布、解析失败、缺失材料和模型输出异常应进入复核或质量控制流程。
- 调整评分规则或 Prompt 时，应保留版本、原因、影响范围和验证结果。

## Python 脚本定位

Python 辅助脚本仍然是当前工作流的一部分。不要因为看到 Python 脚本、Rubric、Prompt、templates、references 就判断它们是废弃内容。

脚本分布包括：

- 根目录 `scripts/`：通用评分、预处理、校准、统计和 Excel 导出。
- `software-project-practicum/scripts/`：实训报告预处理、批量评分和可追踪导出。
- `software-project-practicum/answer-card/scripts/`：答题卡识别、标准答案推断、验证评分和导出。

## 禁止行为

- 不要删除根目录 `SKILL.md`。
- 不要把根目录 `SKILL.md` 改回旧平台 Skill 安装说明。
- 不要删除 README 现有内容。
- 不要重构业务代码来完成纯文档任务。
- 不要移动 Python 脚本。
- 不要删除 `PythonScriptClient` 或 `grader.python.*` 配置，除非用户明确要求迁移。
- 不要把 Rubric、Prompt、templates、references 或脚本误判为废弃内容。
- 不要新增大段营销文案。

## 修改完成后的输出要求

完成修改后，输出应包含：

- 新增或修改文件清单。
- 每项改动的用途。
- 是否发现文档与代码冲突。
- 已执行或未执行的验证步骤。
- 后续建议，仅列对当前任务有直接帮助的事项。
