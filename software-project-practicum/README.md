# 软件项目实训智能阅卷子系统

本目录是智能阅卷系统中面向“软件项目基础实训”场景的子项目，包含后端、前端原型、实训报告批改脚本、答题卡处理材料和相关配置。

当前子系统保留 Python 辅助脚本，用于文档预处理、批量评分和 Excel 导出。这些脚本是现有工作流的一部分，不属于特定助手平台的专属依赖。

## 评分范围

主要面向以下材料：

- 需求规格说明书
- 项目概要设计说明书
- 项目详细设计说明书
- 答题卡或考试类材料，见 `answer-card/`

可按任务配置决定是否纳入：

- 实现截图或运行结果截图
- 实训体会和总结内容
- 其他教师指定附件

## 目录结构

```text
software-project-practicum/
├── backend/                 # Spring Boot 后端
├── frontend-prototype/      # Vue 前端原型
├── answer-card/             # 答题卡识别、评分和验证材料
├── scripts/                 # 实训报告批改辅助脚本
├── rubrics/                 # 实训报告 Rubric
├── references/              # 报告模板和参考材料
└── workspace/               # 本地批处理工作区
```

## 工作区约定

```text
workspace/practicum-batch/
├── raw/          # 学生原始提交
├── reference/    # 标准答案、模板或参考材料
├── ir/           # 解析后的中间表示
├── scores/       # 评分结果
├── reports/      # 导出报表
└── logs/         # 运行日志
```

## 脚本流程

如需手动运行旧批处理脚本，可使用：

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\preprocess_student_dirs.py"
```

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\batch_score_reports.py"
```

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\export_traceability_excel.py"
```

在后端联调场景下，Spring Boot 可通过 `backend/src/main/resources/application.yml` 中的 `grader.python.*` 配置调度这些脚本。

## 后端

```powershell
cd software-project-practicum/backend
mvn spring-boot:run
```

默认地址：

```text
http://localhost:8080
```

## 前端

```powershell
cd software-project-practicum/frontend-prototype
npm install
npm run dev
```

## 输入要求

- 建议每个学生一个独立文件夹。
- 文件夹内可包含需求、概要设计、详细设计等文档。
- 支持 `.doc`、`.docx`、`.pdf` 等格式，具体能力取决于当前脚本和本机环境。
- `.doc` 文件可能需要通过 Microsoft Word 或转换脚本转为 `.docx` 后再处理。
