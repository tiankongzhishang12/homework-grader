CREATE DATABASE IF NOT EXISTS homework_grader
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE homework_grader;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS organization_unit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  parent_id BIGINT NULL COMMENT '父节点ID，学校节点为NULL',

  unit_code VARCHAR(50) NOT NULL COMMENT '组织编码',
  unit_name VARCHAR(100) NOT NULL COMMENT '组织名称',
  unit_type VARCHAR(30) NOT NULL COMMENT 'SCHOOL/COLLEGE/MAJOR/CLASS',

  grade_year INT NULL COMMENT '班级所属年级，仅CLASS类型使用',

  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序号',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  parent_key BIGINT GENERATED ALWAYS AS (IFNULL(parent_id, 0)) STORED,

  CONSTRAINT fk_org_parent
    FOREIGN KEY (parent_id) REFERENCES organization_unit(id),

  CONSTRAINT chk_org_unit_type
    CHECK (unit_type IN ('SCHOOL', 'COLLEGE', 'MAJOR', 'CLASS')),

  CONSTRAINT chk_org_grade_year
    CHECK (
      (unit_type = 'CLASS' AND grade_year IS NOT NULL)
      OR
      (unit_type <> 'CLASS' AND grade_year IS NULL)
    ),

  UNIQUE KEY uk_org_parent_code (parent_key, unit_code),

  KEY idx_org_parent (parent_id),
  KEY idx_org_type (unit_type),
  KEY idx_org_status (status),
  KEY idx_org_sort (parent_id, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS teacher (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  org_unit_id BIGINT NOT NULL COMMENT '教师主归属单位',

  teacher_no VARCHAR(50) NOT NULL,
  teacher_name VARCHAR(50) NOT NULL,
  phone VARCHAR(30) NULL,
  email VARCHAR(100) NULL,

  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_teacher_org
    FOREIGN KEY (org_unit_id) REFERENCES organization_unit(id),

  UNIQUE KEY uk_teacher_no (teacher_no),
  KEY idx_teacher_org (org_unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS student (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  class_org_id BIGINT NOT NULL COMMENT '学生当前行政班级',

  student_no VARCHAR(50) NOT NULL,
  student_name VARCHAR(50) NOT NULL,
  gender VARCHAR(10) NULL,
  enrollment_year INT NOT NULL,

  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_student_class_org
    FOREIGN KEY (class_org_id) REFERENCES organization_unit(id),

  UNIQUE KEY uk_student_no (student_no),
  KEY idx_student_class_org (class_org_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS course (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  course_code VARCHAR(50) NOT NULL,
  course_name VARCHAR(100) NOT NULL,
  credit DECIMAL(4,1) NULL,
  course_type VARCHAR(50) NULL,

  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uk_course_code (course_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS course_offering (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  course_id BIGINT NOT NULL,
  org_unit_id BIGINT NOT NULL COMMENT '开课单位，通常为COLLEGE或后续扩展的DEPARTMENT',

  academic_year VARCHAR(20) NOT NULL,
  term VARCHAR(20) NOT NULL,
  offering_name VARCHAR(100) NOT NULL,

  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uk_course_offering (
    course_id,
    org_unit_id,
    academic_year,
    term,
    offering_name
  ),

  CONSTRAINT fk_course_offering_course
    FOREIGN KEY (course_id) REFERENCES course(id),

  CONSTRAINT fk_course_offering_org
    FOREIGN KEY (org_unit_id) REFERENCES organization_unit(id),

  KEY idx_course_offering_org (org_unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS teaching_class (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,

  course_offering_id BIGINT NOT NULL,
  class_code VARCHAR(50) NOT NULL,
  class_name VARCHAR(100) NOT NULL,

  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uk_teaching_class (course_offering_id, class_code),

  CONSTRAINT fk_teaching_class_offering
    FOREIGN KEY (course_offering_id) REFERENCES course_offering(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
