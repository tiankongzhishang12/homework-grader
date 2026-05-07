# Backend Checklist

## Before Editing

- Confirm current Java and Spring versions in `backend/pom.xml`.
- Check `application.yml` for datasource, upload limits, workspace root, and `grader.python.*`.
- Search for frontend callers in `frontend-prototype/src/api/services.ts`.
- Search SQL table definitions in `database/organization_schema_v2.sql` and `database/grading_schema_v2.sql`.
- If changing grading, review `GradingWorkflowService`, `PythonScriptClient`, export scripts, and final result tables.

## Implementation Rules

- Keep Java 8 compatibility unless the user asks for an upgrade.
- Preserve `PythonScriptClient` and `grader.python.*` unless explicitly migrating the workflow.
- Use existing `ApiResponse` response style.
- Keep JDBC changes scoped; update `CrudJdbcRepository` table allowlist only when schema supports it.
- Validate upload paths and never trust user-supplied file paths.
- For score, review, publish, and export operations, preserve evidence, run status, teacher identity, and timestamps where available.

## Verification

- For backend-only changes, prefer `mvn -q compile` from `software-project-practicum/backend`.
- For API contract changes, verify relevant frontend API clients and route views still match.
- For Python scheduling changes, run or dry-run the configured script command when feasible.
- For DB changes, document execution order and rollback notes; do not alter SQL schema for documentation tasks.

## Output Notes

Report:

- files changed;
- API or schema impact;
- Python script impact;
- tests or checks run;
- any document-code conflicts found.
