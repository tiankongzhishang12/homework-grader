# Minimal Demo Full Grading 验收计划

## 1. 验收目标

本次验收只验证 Python full grading 的最小闭环产物：

```text
software-project-practicum/workspace/minimal-demo/ir/anon-001.json
-> software-project-practicum/scripts/batch_score_reports.py
-> software-project-practicum/workspace/minimal-demo/scores/anon-001.json
```

本次不验证前端、不验证权限、不验证导出，也不执行后端 `/api/assessments/{id}/grading/start`。

## 2. 当前前置条件

当前已具备以下文件：

- `software-project-practicum/grader-config.minimal-demo.yaml`
- `software-project-practicum/workspace/minimal-demo/student-mapping.csv`
- `software-project-practicum/workspace/minimal-demo/ir/anon-001.json`

其中 `grader-config.minimal-demo.yaml` 指向 `grading.workspace_path: "workspace/minimal-demo"`，因此 Python full grading 按该配置运行时，应读取 `workspace/minimal-demo/ir/*.json`，并写入 `workspace/minimal-demo/scores/*.json`。

## 3. Full Grading 命令

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe .\software-project-practicum\scripts\batch_score_reports.py --config .\software-project-practicum\grader-config.minimal-demo.yaml
```

该命令可能调用模型 API。执行前需要确认：

- `OPENAI_API_KEY` 或配置文件中的 `openai.api_key` 可用；
- `OPENAI_BASE_URL` 或配置文件中的 `openai.base_url` 可访问；
- `openai.model` 配置的模型名称有效；
- 当前网络能够访问对应 OpenAI-compatible API 服务。

## 4. 评分结果检查

命令执行完成后，应检查：

```text
software-project-practicum/workspace/minimal-demo/scores/anon-001.json
```

重点检查字段：

- `student_id = anon-001`
- `dimension_scores` 不为空；
- `raw_total_score` 或 `percentile_score` 至少存在一个；
- `overall_confidence` 存在；
- `review_flag` 存在。

如果 `progress.json` 中 `completed_ids` 包含 `anon-001` 且 `failed_ids` 为空，可作为 Python full grading 产物生成成功的辅助证据。

## 5. 失败排查

常见失败原因：

- `OPENAI_API_KEY` 缺失，且配置文件中没有可用 `openai.api_key`；
- `OPENAI_BASE_URL` 或 `grader-config.minimal-demo.yaml` 中的 `openai.base_url` 不可用；
- `model` 名称错误或目标服务不支持该模型；
- `ir/anon-001.json` 内容异常，例如预处理错误、关键字段缺失或 JSON 非法；
- `rubric_path` 配置错误，导致 Rubric 文件无法加载；
- 网络或 API 请求超时；
- 模型返回内容不是合法 JSON，导致评分 JSON 输出解析失败。

## 6. 后端入库说明

当前后端 `application.yml` 中：

```yaml
grader:
  workspace-root: ../workspace/practicum-batch
```

也就是说，Java 侧 `GradingResultImportService` 默认仍从 `practicum-batch` 工作区读取：

- `student-mapping.csv`
- `scores/*.json`

而不是从 `minimal-demo` 工作区读取。

如果要让后端导入 `minimal-demo/scores`，推荐路径有两种：

### 方案 A：复用现有 import-only 验收

临时将以下文件复制到 `software-project-practicum/workspace/practicum-batch/` 对应位置：

- `software-project-practicum/workspace/minimal-demo/student-mapping.csv`
- `software-project-practicum/workspace/minimal-demo/scores/anon-001.json`

然后使用现有 import-only 验收 Java 入库链路。

优点是无需修改后端配置或代码，适合当前最小验收。

### 方案 B：后续新增后端 minimal-demo 支持

后续单独新增后端 `minimal-demo` profile，或让导入接口支持 workspace 参数。

优点是路径更清晰，适合后续自动化演示或多工作区验收；缺点是需要单独设计配置、接口边界和权限约束。

本计划只说明上述两种方案，不实现。

## 7. 推荐验收顺序

1. 确认 `minimal-demo` preprocess 已 PASS。
2. 确认 `grader-config.minimal-demo.yaml` 的 OpenAI API Key、base_url、model 配置正确。
3. 手动执行 `batch_score_reports.py` full grading 命令。
4. 检查 `software-project-practicum/workspace/minimal-demo/scores/anon-001.json`。
5. 如果 `scores/anon-001.json` 正常，再使用 import-only 验收 Java 入库。
6. 最后才考虑完整后端 `/api/assessments/{id}/grading/start` 链路。

## 8. 明确结论

当前下一步最推荐先手动运行 Python full grading，验证 `minimal-demo/scores/anon-001.json` 产物是否稳定生成。

在 Python scores 产物确认正常前，不建议马上改前端、权限或完整后端 grading/start 链路。Java 入库应先复用 import-only 验收，待 Python full grading 产物稳定后，再决定是否新增后端 `minimal-demo` profile 或 workspace 参数支持。
