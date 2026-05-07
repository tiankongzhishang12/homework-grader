# Table Domain Map

Based on `database/organization_schema_v2.sql` and `database/grading_schema_v2.sql`.

## Organization And People

| Table | Domain Purpose | Key Relations |
| --- | --- | --- |
| `organization_unit` | School, college, major, and class hierarchy. | Self-reference via `parent_id`; unique `(parent_key, unit_code)`; indexes for parent/type/status/sort. |
| `teacher` | Teacher master data. | `org_unit_id` references `organization_unit`; unique `teacher_no`. |
| `student` | Student master data and administrative class. | `class_org_id` references `organization_unit`; unique `student_no`. |

## Course And Teaching

| Table | Domain Purpose | Key Relations |
| --- | --- | --- |
| `course` | Course catalog. | unique `course_code`. |
| `course_offering` | A course opened by an org unit in academic year/term. | references `course` and `organization_unit`; unique course/offering identity. |
| `teaching_class` | Teaching class under a course offering. | references `course_offering`; unique `(course_offering_id, class_code)`. |
| `course_offering_teacher` | Teacher assignment and role for an offering. | references `course_offering` and `teacher`; unique `(course_offering_id, teacher_id, role)`. |
| `teaching_class_student` | Student enrollment in teaching class. | references `teaching_class` and `student`; unique `(teaching_class_id, student_id)`. |

## Assessment Configuration

| Table | Domain Purpose | Key Relations |
| --- | --- | --- |
| `assessment` | Assignment, exam, or grading task. | references `course_offering`; unique `(course_offering_id, title)`. |
| `assessment_template` | Versioned assessment template. | references `assessment`; unique `(assessment_id, version_no)`. |
| `question_definition` | Question or scoreable section. | references `assessment_template`; unique `(template_id, question_no)`. |
| `rubric_definition` | Rubric item or scoring dimension. | references `assessment_template`; unique `(template_id, rubric_code)`. |
| `standard_answer` | Versioned answer text or JSON for a question. | references `question_definition`. |
| `answer_card_layout` | Page and region coordinates for answer-card grading. | references `assessment_template`; optionally references `question_definition`. |

## Submission And Extraction

| Table | Domain Purpose | Key Relations |
| --- | --- | --- |
| `submission` | Student submission attempt. | references `assessment` and `student`; unique `(assessment_id, student_id, attempt_no)`. |
| `submission_asset` | Original or derived file asset for a submission. | references `submission`; optional self-reference `source_asset_id`; unique `(submission_id, asset_type, version_no)`. |
| `extraction_run` | OCR/VLM/parser extraction run for a submission. | references `submission`; optional `result_asset_id` references `submission_asset`. |
| `extraction_result` | Structured extraction content. | references `extraction_run`; stores text and JSON content. |

## Grading And Results

| Table | Domain Purpose | Key Relations |
| --- | --- | --- |
| `grading_run` | AI/manual/batch grading run. | references `submission`; optional `extraction_run`; stores model, rubric version, total score, confidence, status. |
| `score_item_result` | Per-question or per-rubric score item. | references `grading_run`; optional `question_definition` and `rubric_definition`; stores evidence, confidence, review flag, comments. |
| `final_result` | Final submission result selected for teacher review. | references `submission`, optional `grading_run`, optional confirming `teacher`; unique `submission_id`. |
| `course_grade` | Aggregated course-level grade for a student. | references `course_offering` and `student`; unique `(course_offering_id, student_id)`. |
| `grade_publish_record` | Grade publishing audit record. | optional references `assessment` and `course_offering`; references publishing `teacher`. |

## Seed Data

The current checked SQL files define schema only. They do not include seed `INSERT` statements in the scanned content. If adding seed data, keep it separate or clearly marked, and do not mix irreversible production data operations with schema creation.
