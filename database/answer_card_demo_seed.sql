USE homework_grader;

SET NAMES utf8mb4;

SET @demo_task_id = 'answer-card-demo';
SET @demo_assessment_title = '答题卡评分联调测试';

CREATE TABLE IF NOT EXISTS auth_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  password_hash VARCHAR(100) NOT NULL,
  display_name VARCHAR(50) NOT NULL,
  user_type VARCHAR(30) NOT NULL,
  teacher_id BIGINT NULL,
  student_id BIGINT NULL,
  status TINYINT NOT NULL DEFAULT 1,
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_auth_user_username (username),
  CONSTRAINT fk_auth_user_teacher FOREIGN KEY (teacher_id) REFERENCES teacher(id),
  CONSTRAINT fk_auth_user_student FOREIGN KEY (student_id) REFERENCES student(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DELETE sir FROM score_item_result sir
JOIN grading_run gr ON gr.id = sir.grading_run_id
JOIN submission s ON s.id = gr.submission_id
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE fr FROM final_result fr
JOIN submission s ON s.id = fr.submission_id
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE gr FROM grading_run gr
JOIN submission s ON s.id = gr.submission_id
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE er FROM extraction_result er
JOIN extraction_run xr ON xr.id = er.extraction_run_id
JOIN submission s ON s.id = xr.submission_id
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE xr FROM extraction_run xr
JOIN submission s ON s.id = xr.submission_id
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE s FROM submission s
JOIN assessment a ON a.id = s.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE qd FROM question_definition qd
JOIN assessment_template t ON t.id = qd.template_id
JOIN assessment a ON a.id = t.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE t FROM assessment_template t
JOIN assessment a ON a.id = t.assessment_id
WHERE a.title = @demo_assessment_title;

DELETE FROM assessment WHERE title = @demo_assessment_title;
DELETE FROM teaching_class_student WHERE student_id IN (SELECT id FROM student WHERE student_no IN ('2023214327', '2023214329', '2023214345'));
DELETE FROM course_offering_teacher WHERE teacher_id IN (SELECT id FROM teacher WHERE teacher_no = 'T-DEMO-001');
DELETE FROM teaching_class WHERE class_code = 'ANSWER-CARD-DEMO-CLASS';
DELETE FROM student WHERE student_no IN ('2023214327', '2023214329', '2023214345');
DELETE FROM course_offering WHERE offering_name = '软件需求分析-答题卡联调';
DELETE FROM course WHERE course_code = 'SE-REQ-DEMO';
DELETE FROM auth_user WHERE username = 'teacher';
DELETE FROM teacher WHERE teacher_no = 'T-DEMO-001';
DELETE FROM organization_unit WHERE unit_code = 'ANSWER-CARD-DEMO-CLASS';
DELETE FROM organization_unit WHERE unit_code = 'SE-DEMO-MAJOR';
DELETE FROM organization_unit WHERE unit_code = 'CST-DEMO-COLLEGE';
DELETE FROM organization_unit WHERE unit_code = 'CQUPT-DEMO-SCHOOL';

INSERT INTO organization_unit (parent_id, unit_code, unit_name, unit_type, grade_year, sort_order)
VALUES (NULL, 'CQUPT-DEMO-SCHOOL', '演示学校', 'SCHOOL', NULL, 1);
SET @school_id = LAST_INSERT_ID();

INSERT INTO organization_unit (parent_id, unit_code, unit_name, unit_type, grade_year, sort_order)
VALUES (@school_id, 'CST-DEMO-COLLEGE', '计算机科学与技术学院', 'COLLEGE', NULL, 1);
SET @college_id = LAST_INSERT_ID();

INSERT INTO organization_unit (parent_id, unit_code, unit_name, unit_type, grade_year, sort_order)
VALUES (@college_id, 'SE-DEMO-MAJOR', '软件工程', 'MAJOR', NULL, 1);
SET @major_id = LAST_INSERT_ID();

INSERT INTO organization_unit (parent_id, unit_code, unit_name, unit_type, grade_year, sort_order)
VALUES (@major_id, 'ANSWER-CARD-DEMO-CLASS', '2023级软件工程答题卡测试班', 'CLASS', 2023, 1);
SET @class_org_id = LAST_INSERT_ID();

INSERT INTO teacher (org_unit_id, teacher_no, teacher_name, phone, email)
VALUES (@college_id, 'T-DEMO-001', '演示教师', '13800000000', 'teacher@example.com');
SET @teacher_id = LAST_INSERT_ID();

INSERT INTO auth_user (username, password_hash, display_name, user_type, teacher_id, status)
VALUES (
  'teacher',
  '$2a$10$YwfJBEY63.ah3F/I5QxoleZBkTFgloUigyOCQBvhXTYKrfkvnyeZy',
  '演示教师',
  'TEACHER',
  @teacher_id,
  1
);

INSERT INTO student (class_org_id, student_no, student_name, gender, enrollment_year)
VALUES
  (@class_org_id, '2023214327', '王志怡', '女', 2023),
  (@class_org_id, '2023214329', '李丹阳', '女', 2023),
  (@class_org_id, '2023214345', '张翼', '男', 2023);

INSERT INTO course (course_code, course_name, credit, course_type)
VALUES ('SE-REQ-DEMO', '软件需求分析', 3.0, '专业课');
SET @course_id = LAST_INSERT_ID();

INSERT INTO course_offering (course_id, org_unit_id, academic_year, term, offering_name)
VALUES (@course_id, @college_id, '2025-2026', '2', '软件需求分析-答题卡联调');
SET @offering_id = LAST_INSERT_ID();

INSERT INTO teaching_class (course_offering_id, class_code, class_name)
VALUES (@offering_id, 'ANSWER-CARD-DEMO-CLASS', '2023级软件工程答题卡测试班');
SET @teaching_class_id = LAST_INSERT_ID();

INSERT INTO course_offering_teacher (course_offering_id, teacher_id, role)
VALUES (@offering_id, @teacher_id, 'PRIMARY');

INSERT INTO teaching_class_student (teaching_class_id, student_id, join_status)
SELECT @teaching_class_id, id, 'ACTIVE'
FROM student
WHERE student_no IN ('2023214327', '2023214329', '2023214345');

INSERT INTO assessment (
  course_offering_id, title, assessment_type, submission_format,
  grading_mode, total_score, weight, due_at, allow_resubmit
)
VALUES (
  @offering_id, @demo_assessment_title, 'EXAM', 'ANSWER_CARD',
  'AUTO_WITH_REVIEW', 100.00, 30.00, '2026-04-30 23:59:59', 0
);
SET @assessment_id = LAST_INSERT_ID();

INSERT INTO assessment_template (assessment_id, template_name, template_type, version_no, total_score)
VALUES (@assessment_id, '软件需求答题卡模板', 'ANSWER_CARD', 1, 100.00);
SET @template_id = LAST_INSERT_ID();

INSERT INTO question_definition (template_id, question_no, question_type, section_name, max_score, scoring_rule, sort_order)
VALUES
  (@template_id, 'single_choice', 'SECTION', '单项选择题', 20.00, '10题，每题2分。', 1),
  (@template_id, 'true_false', 'SECTION', '判断题', 10.00, '10题，每题1分。', 2),
  (@template_id, 'fill_blank', 'SECTION', '填空题', 10.00, '5题，每题2分。', 3),
  (@template_id, 'short_answer', 'SECTION', '简答题', 20.00, '4题，按评分要点评分。', 4),
  (@template_id, 'comprehensive', 'SECTION', '综合建模题', 40.00, '用例图、E-R图、DFD等综合评分。', 5);

SET @q_single = (SELECT id FROM question_definition WHERE template_id = @template_id AND question_no = 'single_choice');
SET @q_tf = (SELECT id FROM question_definition WHERE template_id = @template_id AND question_no = 'true_false');
SET @q_fill = (SELECT id FROM question_definition WHERE template_id = @template_id AND question_no = 'fill_blank');
SET @q_short = (SELECT id FROM question_definition WHERE template_id = @template_id AND question_no = 'short_answer');
SET @q_comp = (SELECT id FROM question_definition WHERE template_id = @template_id AND question_no = 'comprehensive');

SET @s_wzy = (SELECT id FROM student WHERE student_no = '2023214327');
SET @s_ldy = (SELECT id FROM student WHERE student_no = '2023214329');
SET @s_zy = (SELECT id FROM student WHERE student_no = '2023214345');

INSERT INTO submission (assessment_id, student_id, attempt_no, submit_status, submitted_at, source_platform, source_submission_id)
VALUES
  (@assessment_id, @s_wzy, 1, 'SUBMITTED', '2026-04-18 10:00:00', 'ANSWER_CARD_DEMO', '2023214327_王志怡'),
  (@assessment_id, @s_ldy, 1, 'SUBMITTED', '2026-04-18 10:02:00', 'ANSWER_CARD_DEMO', '2023214329_李丹阳'),
  (@assessment_id, @s_zy, 1, 'SUBMITTED', '2026-04-18 10:04:00', 'ANSWER_CARD_DEMO', '2023214345_张翼');

SET @sub_wzy = (SELECT id FROM submission WHERE assessment_id = @assessment_id AND student_id = @s_wzy);
SET @sub_ldy = (SELECT id FROM submission WHERE assessment_id = @assessment_id AND student_id = @s_ldy);
SET @sub_zy = (SELECT id FROM submission WHERE assessment_id = @assessment_id AND student_id = @s_zy);

INSERT INTO extraction_run (submission_id, extractor_type, extractor_name, model_name, prompt_version, status)
VALUES
  (@sub_wzy, 'ANSWER_CARD', 'validation-run-system-extracted', 'vision-pipeline-demo', 'v1', 'COMPLETED'),
  (@sub_ldy, 'ANSWER_CARD', 'validation-run-system-extracted', 'vision-pipeline-demo', 'v1', 'COMPLETED'),
  (@sub_zy, 'ANSWER_CARD', 'validation-run-system-extracted', 'vision-pipeline-demo', 'v1', 'COMPLETED');

SET @xr_wzy = (SELECT id FROM extraction_run WHERE submission_id = @sub_wzy);
SET @xr_ldy = (SELECT id FROM extraction_run WHERE submission_id = @sub_ldy);
SET @xr_zy = (SELECT id FROM extraction_run WHERE submission_id = @sub_zy);

INSERT INTO extraction_result (extraction_run_id, result_type, summary_text, content_json)
VALUES
  (@xr_wzy, 'ANSWER_CARD_SUMMARY', '客观题识别清晰，主观题和图形题建议人工复核。', JSON_OBJECT('paper_id', '2023214327_王志怡', 'source', 'system-reports')),
  (@xr_ldy, 'ANSWER_CARD_SUMMARY', '部分填空题和图形题存在识别不确定，建议人工复核。', JSON_OBJECT('paper_id', '2023214329_李丹阳', 'source', 'system-reports')),
  (@xr_zy, 'ANSWER_CARD_SUMMARY', '综合建模题得分偏低，图形题证据建议人工复核。', JSON_OBJECT('paper_id', '2023214345_张翼', 'source', 'system-reports'));

INSERT INTO grading_run (submission_id, extraction_run_id, run_type, grading_mode, model_name, rubric_version, total_score, confidence, status)
VALUES
  (@sub_wzy, @xr_wzy, 'SYSTEM', 'AUTO_WITH_REVIEW', 'answer-card-demo-scorer', 'answer-card-v1', 89.00, 0.9000, 'COMPLETED'),
  (@sub_ldy, @xr_ldy, 'SYSTEM', 'AUTO_WITH_REVIEW', 'answer-card-demo-scorer', 'answer-card-v1', 70.00, 0.8200, 'COMPLETED'),
  (@sub_zy, @xr_zy, 'SYSTEM', 'AUTO_WITH_REVIEW', 'answer-card-demo-scorer', 'answer-card-v1', 66.00, 0.7800, 'COMPLETED');

SET @gr_wzy = (SELECT id FROM grading_run WHERE submission_id = @sub_wzy);
SET @gr_ldy = (SELECT id FROM grading_run WHERE submission_id = @sub_ldy);
SET @gr_zy = (SELECT id FROM grading_run WHERE submission_id = @sub_zy);

INSERT INTO final_result (submission_id, selected_grading_run_id, final_score, score_source, review_status)
VALUES
  (@sub_wzy, @gr_wzy, 89.00, 'SYSTEM', 'REVIEW_REQUIRED'),
  (@sub_ldy, @gr_ldy, 70.00, 'SYSTEM', 'REVIEW_REQUIRED'),
  (@sub_zy, @gr_zy, 66.00, 'SYSTEM', 'REVIEW_REQUIRED');

INSERT INTO score_item_result (grading_run_id, item_type, question_definition_id, score, max_score, is_correct, needs_review, confidence, evidence_text, comment_text)
VALUES
  (@gr_wzy, 'SECTION', @q_single, 20.00, 20.00, NULL, 0, 0.9500, '1-10题客观题涂卡区识别清晰，单选题全部正确。', '客观题表现稳定。'),
  (@gr_wzy, 'SECTION', @q_tf, 8.00, 10.00, NULL, 0, 0.9000, '11-20题判断题大部分正确，存在少量扣分。', '判断题有小幅失分。'),
  (@gr_wzy, 'SECTION', @q_fill, 10.00, 10.00, NULL, 1, 0.8500, '21-25题填空答案整体可辨识，系统建议保留复核。', '填空题满分但仍建议抽查。'),
  (@gr_wzy, 'SECTION', @q_short, 15.00, 20.00, NULL, 1, 0.8200, '简答题要点覆盖较完整，个别术语表达不够规范。', '简答题整体较好。'),
  (@gr_wzy, 'SECTION', @q_comp, 36.00, 40.00, NULL, 1, 0.7800, '用例图、E-R图和DFD结构基本完整，部分图形符号建议人工复核。', '综合题完成度高。'),

  (@gr_ldy, 'SECTION', @q_single, 16.00, 20.00, NULL, 0, 0.9000, '1、2题与标准答案不一致，其余单选题大部分正确。', '单选题存在开头两题失分。'),
  (@gr_ldy, 'SECTION', @q_tf, 6.00, 10.00, NULL, 0, 0.8400, '判断题存在多处与标准答案不一致。', '判断题失分较明显。'),
  (@gr_ldy, 'SECTION', @q_fill, 8.00, 10.00, NULL, 1, 0.7600, '22题字迹识别不充分，其余填空题基本可辨识。', '填空题有一处复核风险。'),
  (@gr_ldy, 'SECTION', @q_short, 15.00, 20.00, NULL, 1, 0.8000, '简答题多数要点可接受，部分回答展开不足。', '简答题中等偏好。'),
  (@gr_ldy, 'SECTION', @q_comp, 25.00, 40.00, NULL, 1, 0.7000, '用例图、DFD图形较密集，系统边界和关键功能覆盖不够完整。', '综合题建议重点复核。'),

  (@gr_zy, 'SECTION', @q_single, 18.00, 20.00, NULL, 0, 0.9200, '单选题仅少量失分，涂卡区整体清晰。', '客观题基础较好。'),
  (@gr_zy, 'SECTION', @q_tf, 9.00, 10.00, NULL, 0, 0.9000, '判断题整体正确率较高。', '判断题表现较好。'),
  (@gr_zy, 'SECTION', @q_fill, 10.00, 10.00, NULL, 1, 0.8300, '填空题答案基本完整，建议抽样复核字迹。', '填空题满分。'),
  (@gr_zy, 'SECTION', @q_short, 13.00, 20.00, NULL, 1, 0.7600, '简答题覆盖部分要点，但部分说明较简略。', '简答题有明显提升空间。'),
  (@gr_zy, 'SECTION', @q_comp, 16.00, 40.00, NULL, 1, 0.6500, '综合建模题结构缺失较多，图形表达和关键元素覆盖不足。', '综合题是主要失分项。');
