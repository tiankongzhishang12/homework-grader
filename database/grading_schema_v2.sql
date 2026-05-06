USE homework_grader;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS course_offering_teacher (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  course_offering_id BIGINT NOT NULL,
  teacher_id BIGINT NOT NULL,
  role VARCHAR(30) NOT NULL,
  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_offering_teacher_role (course_offering_id, teacher_id, role),
  CONSTRAINT fk_offering_teacher_offering FOREIGN KEY (course_offering_id) REFERENCES course_offering(id),
  CONSTRAINT fk_offering_teacher_teacher FOREIGN KEY (teacher_id) REFERENCES teacher(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS teaching_class_student (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  teaching_class_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  join_status VARCHAR(30) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_teaching_class_student (teaching_class_id, student_id),
  CONSTRAINT fk_teaching_class_student_class FOREIGN KEY (teaching_class_id) REFERENCES teaching_class(id),
  CONSTRAINT fk_teaching_class_student_student FOREIGN KEY (student_id) REFERENCES student(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS assessment (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  course_offering_id BIGINT NOT NULL,
  title VARCHAR(200) NOT NULL,
  assessment_type VARCHAR(30) NOT NULL,
  submission_format VARCHAR(30) NOT NULL,
  grading_mode VARCHAR(30) NOT NULL,
  total_score DECIMAL(6,2) NOT NULL,
  weight DECIMAL(5,2) NULL,
  due_at DATETIME NULL,
  allow_resubmit TINYINT NOT NULL DEFAULT 0,
  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_assessment_title (course_offering_id, title),
  CONSTRAINT fk_assessment_offering FOREIGN KEY (course_offering_id) REFERENCES course_offering(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS assessment_template (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  assessment_id BIGINT NOT NULL,
  template_name VARCHAR(100) NOT NULL,
  template_type VARCHAR(30) NOT NULL,
  version_no INT NOT NULL,
  total_score DECIMAL(6,2) NOT NULL,
  is_active TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_assessment_template_version (assessment_id, version_no),
  CONSTRAINT fk_assessment_template_assessment FOREIGN KEY (assessment_id) REFERENCES assessment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS question_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  template_id BIGINT NOT NULL,
  question_no VARCHAR(20) NOT NULL,
  question_type VARCHAR(30) NOT NULL,
  section_name VARCHAR(100) NULL,
  max_score DECIMAL(6,2) NOT NULL,
  scoring_rule TEXT NULL,
  sort_order INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_question_definition_no (template_id, question_no),
  CONSTRAINT fk_question_definition_template FOREIGN KEY (template_id) REFERENCES assessment_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS rubric_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  template_id BIGINT NOT NULL,
  rubric_code VARCHAR(50) NOT NULL,
  rubric_name VARCHAR(100) NOT NULL,
  max_score DECIMAL(6,2) NOT NULL,
  description TEXT NULL,
  deduction_rule TEXT NULL,
  sort_order INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_rubric_definition_code (template_id, rubric_code),
  CONSTRAINT fk_rubric_definition_template FOREIGN KEY (template_id) REFERENCES assessment_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS standard_answer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  question_definition_id BIGINT NOT NULL,
  answer_text TEXT NULL,
  answer_json JSON NULL,
  version_no INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_standard_answer_question FOREIGN KEY (question_definition_id) REFERENCES question_definition(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS answer_card_layout (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  template_id BIGINT NOT NULL,
  question_definition_id BIGINT NULL,
  page_no INT NOT NULL,
  region_type VARCHAR(30) NOT NULL,
  x INT NOT NULL,
  y INT NOT NULL,
  w INT NOT NULL,
  h INT NOT NULL,
  annotation_x INT NULL,
  annotation_y INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_answer_card_layout_template FOREIGN KEY (template_id) REFERENCES assessment_template(id),
  CONSTRAINT fk_answer_card_layout_question FOREIGN KEY (question_definition_id) REFERENCES question_definition(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS submission (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  assessment_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  attempt_no INT NOT NULL,
  submit_status VARCHAR(30) NOT NULL,
  submitted_at DATETIME NULL,
  is_late TINYINT NOT NULL DEFAULT 0,
  source_platform VARCHAR(50) NULL,
  source_submission_id VARCHAR(100) NULL,
  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_submission_attempt (assessment_id, student_id, attempt_no),
  CONSTRAINT fk_submission_assessment FOREIGN KEY (assessment_id) REFERENCES assessment(id),
  CONSTRAINT fk_submission_student FOREIGN KEY (student_id) REFERENCES student(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS submission_asset (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  submission_id BIGINT NOT NULL,
  asset_type VARCHAR(30) NOT NULL,
  mime_type VARCHAR(100) NULL,
  file_name VARCHAR(255) NOT NULL,
  file_ext VARCHAR(20) NULL,
  file_path VARCHAR(500) NOT NULL,
  file_hash VARCHAR(128) NULL,
  file_size BIGINT NULL,
  page_count INT NULL,
  source_asset_id BIGINT NULL,
  version_no INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_submission_asset_version (submission_id, asset_type, version_no),
  CONSTRAINT fk_submission_asset_submission FOREIGN KEY (submission_id) REFERENCES submission(id),
  CONSTRAINT fk_submission_asset_source FOREIGN KEY (source_asset_id) REFERENCES submission_asset(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS extraction_run (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  submission_id BIGINT NOT NULL,
  extractor_type VARCHAR(30) NOT NULL,
  extractor_name VARCHAR(100) NOT NULL,
  model_name VARCHAR(100) NULL,
  prompt_version VARCHAR(50) NULL,
  status VARCHAR(30) NOT NULL,
  result_asset_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_extraction_run_submission FOREIGN KEY (submission_id) REFERENCES submission(id),
  CONSTRAINT fk_extraction_run_asset FOREIGN KEY (result_asset_id) REFERENCES submission_asset(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS extraction_result (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  extraction_run_id BIGINT NOT NULL,
  result_type VARCHAR(30) NOT NULL,
  summary_text TEXT NULL,
  content_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_extraction_result_run FOREIGN KEY (extraction_run_id) REFERENCES extraction_run(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS grading_run (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  submission_id BIGINT NOT NULL,
  extraction_run_id BIGINT NULL,
  run_type VARCHAR(30) NOT NULL,
  grading_mode VARCHAR(30) NOT NULL,
  model_name VARCHAR(100) NULL,
  rubric_version VARCHAR(50) NULL,
  total_score DECIMAL(6,2) NULL,
  confidence DECIMAL(5,4) NULL,
  status VARCHAR(30) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_grading_run_submission FOREIGN KEY (submission_id) REFERENCES submission(id),
  CONSTRAINT fk_grading_run_extraction FOREIGN KEY (extraction_run_id) REFERENCES extraction_run(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS score_item_result (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  grading_run_id BIGINT NOT NULL,
  item_type VARCHAR(20) NOT NULL,
  question_definition_id BIGINT NULL,
  rubric_definition_id BIGINT NULL,
  score DECIMAL(6,2) NOT NULL,
  max_score DECIMAL(6,2) NOT NULL,
  is_correct TINYINT NULL,
  needs_review TINYINT NOT NULL DEFAULT 0,
  confidence DECIMAL(5,4) NULL,
  evidence_text TEXT NULL,
  evidence_json JSON NULL,
  comment_text TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_score_item_result_run FOREIGN KEY (grading_run_id) REFERENCES grading_run(id),
  CONSTRAINT fk_score_item_result_question FOREIGN KEY (question_definition_id) REFERENCES question_definition(id),
  CONSTRAINT fk_score_item_result_rubric FOREIGN KEY (rubric_definition_id) REFERENCES rubric_definition(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS final_result (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  submission_id BIGINT NOT NULL,
  selected_grading_run_id BIGINT NULL,
  final_score DECIMAL(6,2) NOT NULL,
  score_source VARCHAR(30) NOT NULL,
  review_status VARCHAR(30) NOT NULL,
  confirmed_by_teacher_id BIGINT NULL,
  confirmed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_final_result_submission (submission_id),
  CONSTRAINT fk_final_result_submission FOREIGN KEY (submission_id) REFERENCES submission(id),
  CONSTRAINT fk_final_result_grading_run FOREIGN KEY (selected_grading_run_id) REFERENCES grading_run(id),
  CONSTRAINT fk_final_result_teacher FOREIGN KEY (confirmed_by_teacher_id) REFERENCES teacher(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS course_grade (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  course_offering_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  usual_score DECIMAL(6,2) NULL,
  exam_score DECIMAL(6,2) NULL,
  total_score DECIMAL(6,2) NOT NULL,
  grade_level VARCHAR(20) NULL,
  is_finalized TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_course_grade_student (course_offering_id, student_id),
  CONSTRAINT fk_course_grade_offering FOREIGN KEY (course_offering_id) REFERENCES course_offering(id),
  CONSTRAINT fk_course_grade_student FOREIGN KEY (student_id) REFERENCES student(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS grade_publish_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  assessment_id BIGINT NULL,
  course_offering_id BIGINT NULL,
  publish_scope VARCHAR(30) NOT NULL,
  published_by_teacher_id BIGINT NOT NULL,
  published_at DATETIME NOT NULL,
  publish_status VARCHAR(30) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_grade_publish_assessment FOREIGN KEY (assessment_id) REFERENCES assessment(id),
  CONSTRAINT fk_grade_publish_offering FOREIGN KEY (course_offering_id) REFERENCES course_offering(id),
  CONSTRAINT fk_grade_publish_teacher FOREIGN KEY (published_by_teacher_id) REFERENCES teacher(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
