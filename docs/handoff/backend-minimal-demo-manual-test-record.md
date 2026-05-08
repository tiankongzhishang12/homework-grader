# 后端最小阅卷 Demo 自动验收记录

- 测试时间：2026-05-08T15:02:52
- 测试模式：apply
- 后端地址：`http://localhost:8080`
- 数据库：`root@localhost:3306/homework_grader`
- workspace：`software-project-practicum/workspace/practicum-batch`

## Demo 标识

- assessmentId：`4`
- teacherId：`4`
- studentId：`10`
- submissionId：`10`
- finalResultId：``

## Workspace 文件

- student-mapping.csv：`software-project-practicum\workspace\practicum-batch\student-mapping.csv`
- scores/anon-001.json：`software-project-practicum\workspace\practicum-batch\scores\anon-001.json`

## 接口调用结果

- [FAIL] POST grading/start: HTTP 401: {'success': False, 'message': '未登录或登录已过期。', 'data': None}

## 数据库验证结果

- [FAIL] db final_result exists: count=0
- [FAIL] db score_item_result count: count=0, expected>=2

## 结论

FAIL

## 失败原因

- progress.status is not COMPLETED: None
- final-results response has no rows.
- score-items count too low: 0
- db final_result exists: count=0
- db score_item_result count: count=0, expected>=2
- POST grading/start: HTTP 401: {'success': False, 'message': '未登录或登录已过期。', 'data': None}

## 后续建议

- dry-run 通过后，再显式追加 `--apply` 执行真实验收。
- 若接口返回 401，请传入 `--api-username` 和 `--api-password`，或先确认本地后端认证配置。
- 本脚本只写入或复用 DEMO_* 标识数据，不删除真实数据，不修改 schema。
