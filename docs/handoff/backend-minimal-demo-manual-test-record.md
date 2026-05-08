# 后端最小阅卷 Demo 自动验收记录

- 测试时间：2026-05-08T14:49:47
- 测试模式：dry-run
- 后端地址：`http://localhost:8080`
- 数据库：`root@localhost:3306/homework_grader`
- workspace：`software-project-practicum/workspace/practicum-batch`

## Demo 标识

- assessmentId：``
- teacherId：``
- studentId：``
- submissionId：``
- finalResultId：``

## Workspace 文件

- student-mapping.csv：``
- scores/anon-001.json：``

## 接口调用结果

- dry-run 未调用接口。

## 数据库验证结果

- dry-run 未连接或验证数据库。

## 结论

DRY-RUN

## 失败原因

- 无。

## 后续建议

- dry-run 通过后，再显式追加 `--apply` 执行真实验收。
- 若接口返回 401，请传入 `--api-username` 和 `--api-password`，或先确认本地后端认证配置。
- 本脚本只写入或复用 DEMO_* 标识数据，不删除真实数据，不修改 schema。
