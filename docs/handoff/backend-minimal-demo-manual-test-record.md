# 后端最小阅卷 Demo 自动验收记录

- 测试时间：2026-05-08T16:13:50
- 测试模式：apply
- grading mode: import-only
- 后端地址：`http://localhost:8080`
- 数据库：`root@localhost:3306/homework_grader`
- workspace：`software-project-practicum/workspace/practicum-batch`

## Demo 标识

- assessmentId：`4`
- teacherId：`4`
- studentId：`10`
- submissionId：`10`
- finalResultId：`10`

## Workspace 文件

- student-mapping.csv：`software-project-practicum\workspace\practicum-batch\student-mapping.csv`
- scores/anon-001.json：`software-project-practicum\workspace\practicum-batch\scores\anon-001.json`

## 接口调用结果

- [PASS] api login: HTTP 200: {'success': True, 'message': 'ok', 'data': {'studentId': None, 'role': 'TEACHER', 'teacherId': 3, 'name': '演示教师', 'id': '2', 'username': 'teacher'}}
- [PASS] POST grading/import-scores: HTTP 200: {'success': True, 'message': 'ok', 'data': {'importSummary': {'importedCount': 1, 'skippedCount': 2, 'failedCount': 0, 'imported': ['anon-001.json'], 'skipped': ['anon-002.json: no student mapping for anon-002', 'anon-003.json: no student mapping for anon-003'], 'failed': []}, 'message': 'Some grading results were imported; some were skipped.', 'assessmentId': 4, 'status': 'COMPLETED'}}
- [PASS] GET final-results: HTTP 200: {'success': True, 'message': 'ok', 'data': [{'id': 10, 'submission_id': 10, 'selected_grading_run_id': 10, 'final_score': 88.0, 'score_source': 'AI', 'review_status': 'AI_GENERATED', 'confirmed_by_teacher_id': None, 'confirmed_at': None, 'created_at': '2026-05-08T16:13:50', 'updated_at': '2026-05-08T16:13:50', 'assessment_id': 4, 'student_id': 10, 'attempt_no': 1}]}
- [PASS] GET score-items: HTTP 200: {'success': True, 'message': 'ok', 'data': [{'id': 46, 'grading_run_id': 10, 'item_type': 'RUBRIC', 'question_definition_id': None, 'rubric_definition_id': None, 'score': 45.0, 'max_score': 50.0, 'is_correct': None, 'needs_review': 0, 'confidence': 0.93, 'evidence_text': 'Demo answer covers the expected core requirements.', 'evidence_json': '{"score": 45.0, "evidence": "Demo answer covers the expected core requirements.", "max_score": 50.0, "reasoning": "The response satisfies the key correctness checks.", "confidence": 0.93, "improvement": "Keep the reasoning concise and evidence-based.", "criterion_id": "demo-correctness", "criterion_name": "Correctness"}', 'comment_text': 'Keep the reasoning concise and evidence-based.', 'created_at': '2026-05-08T16:13:50', 'updated_at': '2026-05-08T16:13:50'}, {'id': 47, 'grading_run_id': 10, 'item_type': 'RUBRIC', 'question_definition_id': None, 'rubric_definition_id': None, 'score': 43.0, 'max_score': 50.0, 'is_correct': None, 'needs_review': 0, 'confidence': 0.89, 'evidence_text': 'Demo answer links requirements to implementation notes.', 'evidence_json': '{"score": 43.0, "evidence": "Demo answer links requirements to implementation notes.", "max_score": 50.0, "reasoning": "Traceability is mostly complete for the minimal demo.", "confidence": 0.89, "improvement": "Add more explicit artifact references in real submissions.", "criterion_id": "demo-traceability", "criterion_name": "Traceability"}', 'comment_text': 'Add more explicit artifact references in real submissions.', 'created_at': '2026-05-08T16:13:50', 'updated_at': '2026-05-08T16:13:50'}]}
- [PASS] PUT final-results/confirm: HTTP 200: {'success': True, 'message': 'ok', 'data': {'id': 10}}

## 数据库验证结果

- [PASS] db final_result exists: count=1
- [PASS] db final_score matches demo score: final_score=88.0, expected=88.0
- [PASS] db confirm review_status: review_status=CONFIRMED
- [PASS] db confirmed_at present: confirmed_at=2026-05-08 16:13:51
- [PASS] db score_item_result count: count=2, expected>=2

## 结论

PASS

## 失败原因

- 无。

## 验收模式说明

- import-only 模式：调用 `POST /api/assessments/{id}/grading/import-scores`，不执行 Python 预处理和真实评分，只验证 workspace 评分 JSON 入库链路。
- full grading 模式：调用 `POST /api/assessments/{id}/grading/start`，执行 Python 预处理和真实评分，评分成功后再导入结果。
- `grading/import-scores` 是开发验收 / demo 调试入口，生产化前应增加权限控制，或只在开发环境开放。

## 后续建议

- dry-run 通过后，再显式追加 `--apply` 执行真实验收。
- 若接口返回 401，请传入 `--api-username` 和 `--api-password`，或先确认本地后端认证配置。
- 本脚本只写入或复用 DEMO_* 标识数据，不删除真实数据，不修改 schema。
## 2026-05-08 更新：上传到 raw workspace 手动验收项

本次新增 `submission_asset -> Python raw workspace` 适配。手动验收时：

- 调用 `POST /api/assessments/{id}/submissions/upload` 上传 `.docx` 或 `.pdf`。
- 响应中应包含 `rawWorkspace.synced=true`。
- 检查 `workspace/practicum-batch/raw/{studentNo}_{studentName}/` 下出现同名文件。
- 原 `submission_asset.file_path` 对应文件仍应存在，下载接口不应受影响。
- import-only 验收仍用于快速验证 `scores/*.json` 入库；full grading 验收才依赖 raw workspace、Python 预处理、模型/API 配置和评分脚本。
## 2026-05-09 更新：Python preprocess raw -> IR 验收

- 执行时间：2026-05-09 14:25:04-14:25:54
- 执行命令：`.\\.venv\\Scripts\\python.exe .\\software-project-practicum\\scripts\\preprocess_student_dirs.py`
- raw 输入目录：`software-project-practicum/workspace/practicum-batch/raw/`
- 目标学生 raw 目录：`raw/2024210001_测试学生/`
- 目标输入文件：`raw/2024210001_测试学生/1 校园资料共享项目需求说明.docx`
- 执行结果：命令执行成功，脚本发现 7 个 raw 子目录并写出 7 个 IR 文件。
- student-mapping.csv：已生成 / 更新。
- 关键 mapping 行：`anon-002,2024210001,测试学生`
- 目标 IR 文件：`software-project-practicum/workspace/practicum-batch/ir/anon-002.json`
- IR student_id：`anon-002`
- IR metadata.student_number：`2024210001`
- IR metadata.student_name：`测试学生`
- IR source_files：`raw/2024210001_测试学生/1 校园资料共享项目需求说明.docx`
- IR content.documents：1 个文档。
- IR metadata.document_roles_present：`requirements`
- gate_results 概况：`G-001 requirements present = true`；`G-002 hld missing = false`；`G-003 lld missing = false`；`G-004 no duplicate roles = true`；`G-005 missing roles: hld, lld = false`。
- processing_log：`extract_document success 1 校园资料共享项目需求说明.docx -> role=requirements, conversion=none`
- 错误 IR：目标 `anon-002.json` 不是错误 IR，`error_type` / `error_message` 为空。
- 文档角色识别判断：`requirements` 已识别，说明角色识别部分可用。当前只有一个需求说明书文件，缺少 hld/lld 属于材料不完整，不判定 preprocess 验收失败。
- preprocess 验收结论：PASS。raw 学生文件夹可以被 `preprocess_student_dirs.py` 读取，并生成 `student-mapping.csv` 与目标 IR JSON。
- 注意事项：当前 raw 目录还包含 `assessment-4`、`软件需求答题卡扫描件`、`软件需求答题卡（未修改）` 等非 `数字学号_姓名` 目录，脚本也会为它们生成 mapping/IR。后续 full grading 验收前建议清理或隔离非本次验收目录，避免 mapping 中混入非学生目录。
## 2026-05-09 更新：minimal-demo 独立工作区准备

- 目的：`workspace/practicum-batch/raw` 下存在旧目录和非 `数字学号_姓名` 目录，会导致目标学生在 preprocess 后变成 `anon-002`，并让 `student-mapping.csv` 混入非目标目录。为后续 full grading 验收准备独立、干净、可重复的最小工作区。
- 工作区：`software-project-practicum/workspace/minimal-demo/`
- 已创建子目录：`raw`、`reference`、`ir`、`scores`、`reports`、`logs`
- 源文件路径：`software-project-practicum/workspace/practicum-batch/raw/2024210001_测试学生/1 校园资料共享项目需求说明.docx`
- 目标 raw 路径：`software-project-practicum/workspace/minimal-demo/raw/2024210001_测试学生/1 校园资料共享项目需求说明.docx`
- 配置文件：`software-project-practicum/grader-config.minimal-demo.yaml`
- preprocess 命令：`.\\.venv\\Scripts\\python.exe .\\software-project-practicum\\scripts\\preprocess_student_dirs.py --config .\\software-project-practicum\\grader-config.minimal-demo.yaml`
- preprocess 结果：命令执行成功，只发现 1 个学生目录，并映射为 `anon-001`。
- student-mapping.csv：`software-project-practicum/workspace/minimal-demo/student-mapping.csv`
- 关键 mapping 行：`anon-001,2024210001,测试学生`
- IR 文件：`software-project-practicum/workspace/minimal-demo/ir/anon-001.json`
- IR 关键字段：`student_id=anon-001`，`metadata.student_number=2024210001`，`metadata.student_name=测试学生`，`document_roles_present=requirements`
- 验收结论：PASS。minimal-demo 工作区已可用于后续最小 full grading demo 验收。
- 本次未运行 full grading，未运行 `batch_score_reports.py`，未调用模型，未调用 `/api/assessments/{id}/grading/start`。
