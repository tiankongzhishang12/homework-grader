# Schema Change Checklist

Use this checklist only when the user explicitly asks for database schema changes.

## Planning

- Identify affected SQL files.
- Identify affected backend repositories, services, controllers, and DTO-like maps.
- Identify affected frontend API types, views, and stores.
- Identify affected Python scripts and export formats.
- Decide whether existing data needs migration or backfill.

## Safety

- Preserve audit chain for submissions, extraction, grading, final results, teacher review, and publish records.
- Do not drop evidence, confidence, model, rubric version, teacher identity, or timestamps without explicit approval.
- Keep foreign keys consistent with execution order.
- For Navicat execution, document database name, file order, and whether statements are idempotent.

## Verification

- Execute schema in a local MySQL 8-compatible database when feasible.
- Confirm `CrudJdbcRepository` allowlist matches backend needs.
- Run backend compile after schema-related Java changes.
- Check frontend API and export assumptions.

## Output

Report SQL files changed, migration/backfill notes, affected tables, API impact, Python script impact, and rollback guidance.
