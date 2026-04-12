# 软件项目基础实训批改系统

本目录是一个独立于 `cqupt-final` 的专项批改系统，只用于评阅：

- 需求规格说明书
- 项目概要设计说明书
- 项目详细设计说明书

不纳入评分范围：

- 实现截图 / 运行结果截图
- 实训体会和收获

## 目录结构

```text
software-project-practicum/
├── grader-config.yaml
├── references/
├── rubrics/
├── scripts/
└── workspace/
    └── practicum-batch/
        ├── raw/
        ├── reference/
        ├── ir/
        ├── scores/
        ├── reports/
        └── logs/
```

## 手动迁移

请将以下内容手动移动到本目录：

- 报告模板到 `references/`
- 学生样本目录到 `workspace/practicum-batch/raw/`
- 追踪式 rubric 到 `rubrics/software-project-traceability-rubric.yaml`

## 运行流程

1. 将学生目录放入 `workspace/practicum-batch/raw/`
2. 运行预处理：

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\preprocess_student_dirs.py"
```

3. 运行评分：

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\batch_score_reports.py"
```

4. 导出 Excel：

```powershell
& ".\.venv\Scripts\python.exe" ".\software-project-practicum\scripts\export_traceability_excel.py"
```

## 输入要求

- 每个学生一个文件夹
- 文件夹内应包含三类文档中的大部分：
  - 需求文档
  - 概要设计文档
  - 详细设计文档
- 支持 `.doc` / `.docx` / `.pdf`

`.doc` 会优先通过已安装的 Microsoft Word 自动转换为 `.docx` 后再抽取。
