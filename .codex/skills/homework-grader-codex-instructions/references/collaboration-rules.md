# Collaboration Rules

## Project Context

- Root `SKILL.md` is Codex Project Context, not old platform Skill installation docs.
- `.codex/skills/` contains task-triggered Agent Skills for lower-token collaboration.
- README content should be preserved unless the user explicitly asks to edit it.

## Code First

- If documents conflict with code, follow code and report the conflict.
- Backend stack currently follows `backend/pom.xml`: Spring Boot `2.7.18`, Java `1.8`.
- Routes follow `frontend-prototype/src/router.ts`.
- Tables follow `database/organization_schema_v2.sql` and `database/grading_schema_v2.sql`.

## Preserve Current Workflow

- Do not delete Python scripts because they look like old platform assets.
- Do not delete `PythonScriptClient`.
- Do not delete `grader.python.*`.
- Do not move Rubrics, Prompts, templates, references, or scripts during unrelated work.

## Audit-Sensitive Work

For grading, review, export, and publishing:

- preserve evidence and confidence;
- preserve teacher review or confirmation path;
- preserve final result distinction from raw grading run;
- report any gap that weakens traceability.

## Scope Control

- Keep edits close to the user request.
- Avoid broad refactors in documentation tasks.
- Do not change SQL schema unless schema change is the task.
- Do not upgrade frameworks unless upgrade is the task.
