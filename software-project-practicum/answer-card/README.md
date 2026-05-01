# 答题卡评分第一阶段

本目录实现第一阶段流程：从已批改扫描件中提取教师已给出的分数，输出结构化 JSON 与 Excel。

## 目标

- 输入：`workspace/practicum-batch/raw/软件需求答题卡扫描件/**.jpg`
- 输出：
  - 标准化图片 `answer-card/workspace/phase1/normalized/`
  - 分数区域裁剪图 `answer-card/workspace/phase1/crops/`
  - 单卷解析结果 `answer-card/workspace/phase1/parsed/*.json`
  - 异常待复核清单 `answer-card/workspace/phase1/review/review-list.json`
  - 汇总表 `answer-card/workspace/phase1/exports/answer-card-scores.xlsx`

## 处理思路

1. 读取扫描件。
2. 基于四角黑块估算答题卡边界，裁切并缩放到统一尺寸。
3. 按模板坐标切出总分区、客观题得分区、主观题题号得分区。
4. 使用 `gpt-5.4` 读取这些局部区域中的红色教师批注。
5. 用规则校验分数范围、总分一致性、题号满分约束。
6. 导出 Excel，标记需要人工复核的卷子。

## 运行

先确认当前环境的 Python 解释器可直接运行，并且能访问 `grader-config.yaml` 中配置的 OpenAI 兼容接口。

```powershell
python .\software-project-practicum\answer-card\scripts\extract_scanned_scores.py
python .\software-project-practicum\answer-card\scripts\export_scores_excel.py
```

如果你想先只跑少量样本，可以加：

```powershell
python .\software-project-practicum\answer-card\scripts\extract_scanned_scores.py --limit 5
```

## 可调项

- 模板坐标：`configs/answer_card_template.yaml`
- 默认输入目录：`configs/answer_card_template.yaml`
- 模型与接口地址：复用 `software-project-practicum/grader-config.yaml`

## 说明

- 第一阶段优先提取“老师已经写出的最终分数”，不是自动重判学生答案。
- 如果模型读取和规则校验冲突，结果会进入 `needs_review=true`。
- 若后续你要做第二阶段自动阅卷，可直接复用第一阶段产出的结构化真值结果。
