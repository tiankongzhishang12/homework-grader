# 重庆邮电大学期末试卷智能批改系统技术文档

## 1. 文档概述

本文档面向项目维护者、任课教师和技术实施人员，说明 `homework-grader` 在“重庆邮电大学期末试卷批改”场景下的系统设计、目录组织、核心流程、配置方式、运行方法与质量控制机制。

本项目并非通用聊天式阅卷工具，而是一套围绕“试卷预处理 -> 结构化中间表示 -> 基于评分标准的自动评分 -> Excel 导出 -> 统计质检”构建的批处理评分流水线。针对重庆邮电大学期末试卷，本仓库已经提供了独立工作区、独立配置文件和专项 Rubric，可直接用于同版式试卷的批改。

## 2. 建设目标

系统建设目标如下：

- 将学生 PDF 试卷转换为统一的结构化中间表示，降低后续评分耦合度。
- 将评分标准显式写入 Rubric YAML，保证评分规则可审计、可维护、可复用。
- 对客观题和主观题采用不同评分策略，兼顾机械计分与语义评价。
- 支持批量评分、断点续跑、日志记录、统计分析和 Excel 成绩导出。
- 通过匿名学号、置信度、门禁检查和偏差分析，降低误判风险。

## 3. 适用范围

当前专项方案主要适用于以下条件：

- 试卷来源为重庆邮电大学期末考试答卷 PDF。
- 试卷版式与当前裁剪预设基本一致。
- 阅卷结构包含选择题、判断题、填空题、简答题、编程题、算法题、白盒测试题等。
- 评分依据来自 `examples/cqupt-final-exam-rubric.yaml` 中定义的真实题号评分标准。

若试卷版式、题号位置、答题区域布局发生明显变化，应先调整预处理裁剪规则，再重新投入批量评分。

## 4. 系统总体架构

系统采用“离线预处理 + 规则驱动评分 + 结果导出”的分层架构，整体分为五层：

1. 输入层  
   教师手工将学生试卷 PDF 放入 `workspace/cqupt-final/raw/`，标准答案材料放入 `workspace/cqupt-final/reference/`。

2. 预处理层  
   `scripts/preprocess.py` 负责读取 PDF，抽取文本、识别客观题涂写区域、转录主观题答题区域，并输出 IR JSON。

3. 评分层  
   `scripts/batch_score.py` 读取 Rubric 与 IR，调用 OpenAI 兼容接口执行逐题评分、汇总分数、生成评语与置信度。

4. 输出层  
   `scripts/export_excel.py` 将评分 JSON 转换为 Excel 成绩表、统计表和明细表。

5. 质检层  
   `scripts/stats.py` 对批次结果进行分布分析、长度偏差、顺序偏差和维度耦合检查。

## 5. 目录与文件组织

CQUPT 专项工作区采用独立目录，避免与历史示例作业混用。

```text
homework-grader/
|- grader-config.cqupt-final.yaml          # CQUPT 专项运行配置
|- examples/
|  `- cqupt-final-exam-rubric.yaml         # CQUPT 期末试卷评分标准
|- scripts/
|  |- preprocess.py                        # 预处理脚本
|  |- batch_score.py                       # 批量评分脚本
|  |- export_excel.py                      # Excel 导出脚本
|  |- stats.py                             # 统计分析脚本
|  `- debug_exam_crops.py                  # 版式裁剪调试脚本
`- workspace/
   `- cqupt-final/
      |- raw/                              # 学生试卷 PDF
      |- reference/                        # 标准答案等参考材料
      |- ir/                               # 预处理后的 IR JSON
      |- scores/                           # 单份试卷评分结果
      |- reports/                          # Excel 与统计报告
      `- logs/                             # 运行日志
```

## 6. 关键技术方案

### 6.1 Rubric 驱动评分

评分标准由 YAML 文件定义，而不是写死在脚本中。CQUPT 专项 Rubric 使用 `raw` 计分模式，以“真实题号 + 单题满分 + 评分规则”为核心组织方式，适用于考试场景下的逐题给分。

Rubric 主要包含：

- 试卷元信息：`id`、`name`、`version`
- 评分模式：`score_mode: raw`
- 总分信息：`max_total_score: 100`
- 门禁规则：用于检查文本提取完整性、题型结构、灰色方块识别提示等
- 逐题 criteria：定义每一道题的题型、分值、标准答案、核心得分点、扣分规则、等价表述
- 评语规则：控制语言、长度和格式

### 6.2 中间表示 IR

IR 是系统内部统一处理格式，用于解耦“文件读取”和“智能评分”。预处理阶段会将原始 PDF 转为 JSON，通常包含：

- 匿名学生 ID
- 原始文本抽取结果
- 学生答案文本
- 元数据，例如字数、段落数
- 客观题识别结果
- 主观题转录结果
- 门禁检查结果

评分阶段只依赖 IR 和 Rubric，不再直接读取原始 PDF，从而便于复查、追踪和复跑。

### 6.3 客观题识别

CQUPT 试卷中选择题和判断题依赖固定版式中的涂写区域识别。系统在 `preprocess.py` 中内置了 CQUPT 相关视觉预设：

- `OBJECTIVE_VISION_PRESET = "cqupt_page1_v1"`
- `SUBJECTIVE_LAYOUT_BY_STEM` 中为 `text1`、`text2`、`text3` 指定了主观题裁剪布局

该方案适合版式稳定的期末试卷。若答题卡布局变化，需先使用调试脚本校正裁剪区域。

### 6.4 主观题评分

简答题、编程题、算法题、白盒测试题采用“标准答案参考 + 关键点覆盖 + 逻辑质量”联合评分，而不是逐字匹配。Rubric 中通过以下字段控制评分：

- `core_points`
- `acceptable_alternatives`
- `full_score_conditions`
- `partial_credit_conditions`
- `zero_score_conditions`
- `deduction_rules`

这种设计可以兼顾规范答案与等价正确表达，更符合试卷阅卷场景。

### 6.5 断点续跑与批次管理

评分脚本会在工作区中维护 `progress.json`，记录：

- 批次 ID
- Rubric ID
- 总任务数
- 已完成、失败、待处理数量
- 处理顺序
- 失败记录
- Token 用量和估算成本

当评分中断时，可通过 `--resume` 继续批次处理，避免重复消耗。

## 7. 核心模块说明

### 7.1 预处理模块

`scripts/preprocess.py` 负责以下工作：

- 扫描输入目录中的 PDF、DOCX、图片等支持格式
- 为每份试卷生成匿名 ID，如 `anon-001`
- 执行文本抽取、图像裁剪、客观题识别、主观题转录
- 结合 Rubric 生成门禁检查结果
- 将结果写入 `workspace/cqupt-final/ir/*.json`

CQUPT 专项预处理的关键点是：同一份试卷既包含整卷 OCR 文本，也包含针对客观题和主观题区域的局部识别结果，便于后续混合评分。

### 7.2 批量评分模块

`scripts/batch_score.py` 是系统主控模块，负责：

- 读取运行配置、Rubric 和工作区路径
- 加载 IR 文件
- 校验 OpenAI API 配置
- 调用模型完成逐题评分
- 计算总分、百分制映射、等级、置信度、评语
- 写入 `scores/*.json`
- 自动导出 Excel
- 自动生成统计报告

本模块支持自定义模型、并发 worker 数、独立配置文件以及失败重试机制。

### 7.3 Excel 导出模块

`scripts/export_excel.py` 负责将评分结果整形成三张工作表：

- 成绩表：学号、姓名、各题得分、卷面总分、百分制、等级、评语摘要、置信度、复核标记、门禁状态
- 统计表：均分、标准差、最高分、最低分、等级分布、各维度均分等
- 明细表：逐题评分明细及理由

如果存在 `student-mapping.csv`，系统会将匿名 ID 映射回真实学号和姓名；如果没有，则保留匿名标识。

### 7.4 统计分析模块

`scripts/stats.py` 用于对评分结果进行事后质量检查，重点关注：

- 分数分布是否过度集中
- 标准差是否异常
- 偏态是否超阈值
- 答卷长度与成绩是否存在显著相关
- 处理顺序与成绩是否存在顺序偏差
- 各题之间是否出现异常耦合

该模块输出 Markdown 报告，可作为人工复核依据。

## 8. CQUPT 专项运行流程

### 8.1 准备阶段

1. 将学生试卷 PDF 放入 `workspace/cqupt-final/raw/`
2. 将标准答案材料放入 `workspace/cqupt-final/reference/`
3. 检查 `grader-config.cqupt-final.yaml`
4. 检查 `examples/cqupt-final-exam-rubric.yaml` 是否与本次试卷一致

### 8.2 预处理阶段

执行：

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\preprocess.py" `
  ".\workspace\cqupt-final\raw" `
  --output ".\workspace\cqupt-final\ir" `
  --rubric ".\examples\cqupt-final-exam-rubric.yaml"
```

预处理完成后，应抽样检查 `ir/*.json`，重点关注：

- 题号是否完整
- 客观题识别是否读取到灰色涂写区域
- 主观题内容是否截断
- OCR 是否丢失关键公式、代码、图示或段落

### 8.3 评分阶段

执行：

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\batch_score.py" `
  --config ".\grader-config.cqupt-final.yaml"
```

脚本将自动：

- 加载工作区和 Rubric
- 顺序随机化处理试卷，减轻位置偏差
- 逐份生成评分 JSON
- 记录日志和批次进度
- 批次结束后导出 Excel 和统计报告

### 8.4 结果复核阶段

建议优先复核以下试卷：

- 门禁未通过的试卷
- 置信度低的试卷
- OCR 明显异常的试卷
- 客观题灰色方块无法可靠识别的试卷
- 主观题答案较短但得分异常高或异常低的试卷

## 9. 配置说明

CQUPT 专项配置文件如下：

```yaml
openai:
  api_key: "..."
  base_url: "http://localhost:8317/v1"
  model: "gpt-5.4"

grading:
  workspace_path: "workspace/cqupt-final"
  rubric_path: "examples/cqupt-final-exam-rubric.yaml"
```

关键配置项说明：

- `api_key`：模型服务认证信息
- `base_url`：OpenAI 兼容接口地址
- `model`：评分模型名称
- `workspace_path`：当前专项工作区
- `rubric_path`：当前试卷评分标准

建议将配置与工作区绑定，避免不同课程或不同批次误用同一 Rubric。

## 10. 输出物说明

系统典型输出包括：

- `workspace/cqupt-final/ir/*.json`  
  预处理后的中间表示文件

- `workspace/cqupt-final/scores/*.json`  
  单份试卷评分结果，包含各题得分、总分、置信度、评语等

- `workspace/cqupt-final/progress.json`  
  批处理进度与失败记录

- `workspace/cqupt-final/reports/grades-*.xlsx`  
  Excel 成绩导出文件

- `workspace/cqupt-final/reports/statistics.md`  
  统计与偏差分析报告

- `workspace/cqupt-final/logs/scoring.log`  
  评分日志

## 11. 质量控制与风险控制

### 11.1 质量控制机制

系统当前采用以下质量控制手段：

- Rubric 明确化：评分标准外显，避免自由发挥
- 门禁检查：对文本过少、题型结构异常、灰色方块提示缺失进行标记
- 匿名化处理：评分阶段使用匿名 ID
- 置信度机制：对不确定结果进行人工复核提示
- 偏差分析：检查长度偏差、顺序偏差、维度耦合
- 日志追踪：保留完整运行日志和中间结果

### 11.2 已知风险

当前方案仍存在以下风险：

- 试卷版式变化会直接影响裁剪与识别结果
- 涂写较浅、扫描倾斜或图片质量差时，客观题识别可能失真
- 主观题如果书写潦草或 OCR 质量差，模型可能基于不完整文本评分
- 若 Rubric 未及时更新，评分结果会与真实题意偏离
- 若标准答案存在多种合理解法但 Rubric 描述不充分，主观题可能低估分数

因此，系统应被定义为“智能辅助阅卷系统”，而不是完全脱离教师的最终判卷系统。

## 12. 维护建议

为保证系统长期可用，建议按以下方式维护：

- 每次考试前先检查 Rubric 是否与本次试卷逐题一致
- 每次更换试卷模板后，先使用裁剪调试脚本验证客观题与主观题区域
- 对低置信度、门禁失败、OCR 异常样本建立人工复核清单
- 保存每次批改的工作区与导出文件，便于复查与追责
- 若计划扩大到更多课程，应按课程或考试类型拆分独立 workspace 与 rubric

## 13. 结论

该项目已经形成一套适用于重庆邮电大学期末试卷批改的专项技术方案。其核心价值在于将试卷批改过程拆分为可配置、可追踪、可批处理、可复核的工程流水线。通过“专项版式预处理 + Rubric 逐题评分 + Excel 输出 + 统计质检”的组合，系统能够显著降低人工批改压力，并为教师保留必要的复核与裁量空间。

后续若继续演进，建议重点投入以下方向：

- 提升版式变化下的自动适配能力
- 增强手写内容识别鲁棒性
- 引入标准答案自动解析与 Rubric 半自动生成能力
- 增加人工复核界面与复评分发机制

