# 智能阅卷系统 Homework Grader

本项目是一个面向课程作业、实训报告和答题卡场景的智能阅卷系统。当前项目重点是用 ChatGPT / OpenAI-compatible 模型、Codex 协作开发能力、Spring Boot 后端、Vue 前端、MySQL 数据库和 Python 辅助脚本，支撑从任务配置、材料上传、批量阅卷、教师复核到成绩导出的完整流程。

本仓库过去曾以旧 Skill 体系组织过一部分评分方法和脚本说明。当前文档已改为项目级说明：不再把仓库定位为某个特定助手平台的 Skill，但保留 Rubric、批处理、质量控制和 Python 辅助脚本等仍在使用的能力。

## 项目目标

- 为教师提供可配置、可追踪、可复核的智能阅卷流程。
- 支持标准答案、评分规则、Rubric、题目区块和导出模板等配置。
- 支持批量处理学生提交，并生成分项得分、总分、置信度、风险标记和评语。
- 支持教师确认、调整、发布成绩，并保留审计记录。
- 支持通过 OpenAI API 或 OpenAI-compatible 网关接入模型。

## 当前工作流程

1. 创建课程、教学班和阅卷任务。
2. 配置标准答案、评分规则、Rubric 和导出模板。
3. 上传或导入学生提交文件。
4. 后端启动批量阅卷流程，必要时调度 Python 辅助脚本完成预处理、评分或导出。
5. 教师在前端查看进度、分项结果、风险标记和学生详情。
6. 教师确认或调整最终成绩。
7. 导出成绩表和分析结果。

这一轮文档清理不改变以上工作流，也不删除任何脚本或接口。

## 技术栈

- 后端：Spring Boot 3、Java 17、Spring JDBC、MySQL
- 前端：Vue 3、TypeScript、Vite、Pinia
- 数据库：MySQL，数据库设计文档和 SQL 位于 `database/`
- 辅助脚本：Python，用于文档预处理、批量评分、答题卡处理、Excel 导出和验证报告
- 模型接入：OpenAI API 或 OpenAI-compatible API

## 目录结构

```text
homework-grader/
├── README.md                         # 项目入口说明
├── SKILL.md                          # Codex 项目协作上下文
├── database/                         # 数据库 SQL 和设计文档
├── scripts/                          # 通用 Rubric 批处理和导出脚本
├── templates/                        # Rubric、Prompt、Schema 模板
├── examples/                         # Rubric 示例
├── references/                       # 评分方法、质控和批处理参考资料
├── software-project-practicum/
│   ├── backend/                      # Spring Boot 后端
│   ├── frontend-prototype/           # Vue 前端原型
│   ├── answer-card/                  # 答题卡识别、评分和验证相关材料
│   ├── scripts/                      # 软件项目实训报告批改辅助脚本
│   └── README.md                     # 子项目说明
└── workspace/                        # 本地工作区和批处理产物
```

## 环境要求

- Java 17
- Maven
- Node.js 和 npm
- Python 3.10 或更高版本
- MySQL 8 或兼容版本
- OpenAI API Key，或兼容 OpenAI API 协议的模型网关

常用模型配置：

```yaml
openai:
  api_key: "your-api-key"
  base_url: "http://your-host:port/v1"
  model: "gpt-5-mini"
```

如果使用本地或学校内网模型网关，可通过 `OPENAI_BASE_URL` 或项目配置文件指定兼容接口地址。

## 后端启动

```powershell
cd software-project-practicum/backend
mvn spring-boot:run
```

默认服务地址：

```text
http://localhost:8080
```

Swagger UI：

```text
http://localhost:8080/swagger-ui.html
```

核心配置位于：

```text
software-project-practicum/backend/src/main/resources/application.yml
```

其中 `grader.python.*` 仍用于当前后端调度 Python 辅助脚本。该配置属于现有工作流的一部分，不是旧助手平台依赖。

## 前端启动

```powershell
cd software-project-practicum/frontend-prototype
npm install
npm run dev
```

前端原型包含任务中心、配置页、批量阅卷、学生详情、结果分析、导出中心等页面。

## Python 辅助脚本

仓库中保留两类 Python 脚本：

- 根目录 `scripts/`：通用 Rubric 批量评分、预处理、校准、统计和 Excel 导出脚本。
- `software-project-practicum/scripts/` 与 `software-project-practicum/answer-card/scripts/`：当前智能阅卷系统相关的实训报告、答题卡处理和验证脚本。

这些脚本不是某个助手平台的专属能力。当前项目可继续通过 ChatGPT / OpenAI-compatible API 调用模型，也可由 Spring Boot 后端按配置调度部分脚本。

安装依赖示例：

```powershell
pip install -r scripts/requirements.txt
```

## 评分规则与质量控制

系统继续沿用 Rubric-driven 的评分思想：

- 所有评分维度、权重、满分和判分依据应来自 Rubric 或标准答案配置。
- 模型输出应包含证据、分项得分、扣分原因、置信度和建议。
- 低置信度、异常分布、解析失败和门禁不通过的结果应进入教师复核。
- 最终成绩以教师确认或调整后的结果为准。

推荐的质控流程：

1. Plan：配置 Rubric、标准答案、样例和任务参数。
2. Do：批量解析、评分、生成评语。
3. Check：检查分布、置信度、异常样本和教师抽检结果。
4. Act：确认成绩、调整规则、导出并沉淀下一轮改进。

## 数据库

数据库脚本和说明位于 `database/`。当前后端主要围绕组织结构、课程、教学班、考核任务、提交、评分运行、分项结果、最终成绩和发布记录等表展开。

建议优先查看：

- `database/grading_schema_v2.sql`
- `database/organization_schema_v2.sql`
- `database/homework_grader_schema.html`

## 协作说明

- 使用 Codex 修改项目时，优先阅读 `SKILL.md` 获取项目上下文。
- 不要把 Python 辅助脚本误判为旧 Skill 体系依赖；只有旧 Skill 安装说明、特定模型平台推荐和供应商绑定叙事属于应清理内容。
- 修改工作流代码前，需要先确认是否会影响批量阅卷、导出和后端脚本调度。
- 文档、前端、后端、数据库和脚本可以分阶段演进，避免一次性删除仍在使用的能力。

## License

MIT
