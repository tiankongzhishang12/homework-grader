---
name: homework-grader-backend
description: Use this skill for Spring Boot backend work in Homework Grader, including controllers, services, JDBC repositories, authentication, file upload, grading workflow APIs, PythonScriptClient integration, export APIs, and backend configuration. Trigger when changing or reviewing backend Java code, application.yml, Maven dependencies, API behavior, grading orchestration, uploads, downloads, or Python script scheduling.
---

# Homework Grader Backend

Use this skill when a task touches the Spring Boot backend or backend-facing contracts.

Backend implementation rule:

- When adding or changing backend behavior, add focused SLF4J logs at important lifecycle points: request/start, validation decisions, successful completion with key IDs/status/counts/file paths, and failure paths with concise reason plus exception stack trace. Do not log secrets, long student answers, evidence text, full config files, or large JSON payloads.

Before editing, read the relevant reference files:

- `references/backend-architecture.md` for current backend structure and code facts.
- `references/backend-api-map.md` for controller endpoints.
- `references/backend-checklist.md` for implementation and review checks.

Keep detailed architecture notes in `references/`; keep this SKILL.md small so Codex only loads deeper context when needed.
