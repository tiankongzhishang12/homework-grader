# Codex Task Instruction Template

## 任务名

用一句话说明任务，例如：`补齐教师复核时 confirmed_at 的写入和前端展示`。

## 任务背景

说明业务场景、当前问题、相关代码位置和为什么现在要做。

## 任务目标

列出本次必须完成的结果。目标要能验收，不要写泛泛的“优化体验”。

## 修改范围

列出允许修改的目录或文件，例如：

- `software-project-practicum/backend/src/main/java/...`
- `software-project-practicum/frontend-prototype/src/...`
- `.codex/skills/...`

## 非目标

明确本次不做的事，例如：

- 不升级 Spring Boot 或 Java。
- 不修改数据库表结构。
- 不迁移 Python 脚本。

## 后端影响

说明涉及的 controllers、services、repositories、configuration、API contracts、auth、upload、export 或 Python scheduling。

## 前端影响

说明涉及的 routes、views、stores、API clients、loading/error states 和 teacher workflow。

## 数据库影响

说明涉及的表、字段、索引、外键、迁移、seed data、Navicat 执行步骤或“无数据库变更”。

## Python 脚本影响

说明是否影响：

- 根目录 `scripts/`
- `software-project-practicum/scripts/`
- `software-project-practicum/answer-card/scripts/`

如果无影响，明确写“无 Python 脚本变更”。

## 验收步骤

列出可执行检查，例如：

- `mvn -q compile`
- `npm run build`
- 指定 API 手动请求
- 指定页面浏览器验证
- SQL dry run 或 Navicat 执行顺序检查

## 输出要求

要求 Codex 完成后输出：

- 文件清单；
- 行为变化；
- API/前端/数据库/Python 影响；
- 验证结果；
- 发现的文档与代码冲突；
- 后续建议。
