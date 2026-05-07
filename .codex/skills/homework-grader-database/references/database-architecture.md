# Database Architecture

## Source Files

- `database/organization_schema_v2.sql`
- `database/grading_schema_v2.sql`
- `database/homework_grader_schema.html`

`organization_schema_v2.sql` creates database `homework_grader` and core school/course tables.

`grading_schema_v2.sql` assumes `USE homework_grader;` and adds teaching membership, assessments, templates, submissions, extraction, grading, final results, course grades, and publish records.

## Execution Order

For a fresh local database, execute in this order:

1. `database/organization_schema_v2.sql`
2. `database/grading_schema_v2.sql`

`grading_schema_v2.sql` has foreign keys to tables created by `organization_schema_v2.sql`.

## MySQL And Charset

The schema uses:

- `utf8mb4`
- `utf8mb4_0900_ai_ci`
- InnoDB
- generated column `parent_key`
- `CHECK` constraints
- `JSON` columns

Use MySQL 8 or a compatible version. If using Navicat, execute each SQL file in order against a MySQL 8 connection and confirm the active database is `homework_grader` before running the second file.

## Backend Relationship

`CrudJdbcRepository` explicitly allowlists all current table names. If a schema change adds a table that the backend must access through generic CRUD, update the allowlist intentionally and verify all identifiers are validated.

## Audit Relationship

Audit-sensitive grading data spans:

- `submission` and `submission_asset`
- `extraction_run` and `extraction_result`
- `grading_run`
- `score_item_result`
- `final_result`
- `course_grade`
- `grade_publish_record`

Do not collapse these tables into only a final score without preserving traceability.
