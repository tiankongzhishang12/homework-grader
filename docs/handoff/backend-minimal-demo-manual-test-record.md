# Backend Minimal Demo Manual Test Record

- Timestamp: 2026-05-09T15:53:33
- Mode: dry-run
- Grading mode: import-only
- Use existing workspace: yes
- Base URL: `http://localhost:8080`
- Database: `root@localhost:3306/homework_grader`
- Workspace: `software-project-practicum/workspace/practicum-batch`

## Demo IDs

- assessmentId: ``
- teacherId: ``
- studentId: ``
- submissionId: ``
- finalResultId: ``

## Workspace Files

- student-mapping.csv: `software-project-practicum\workspace\practicum-batch\student-mapping.csv`
- primary score file: `software-project-practicum\workspace\practicum-batch\scores\anon-001.json`
- detected score files: `software-project-practicum\workspace\practicum-batch\scores\anon-001.json, software-project-practicum\workspace\practicum-batch\scores\anon-002.json, software-project-practicum\workspace\practicum-batch\scores\anon-003.json`

## API Results

- No API calls were made in this run.

## Database Checks

- No database checks were run in this mode.

## Conclusion

DRY-RUN

## Failures

- None.

## Mode Notes

- `--apply`: prepares or reuses DEMO_* database rows and calls backend APIs.
- `--apply` without `--use-existing-workspace`: writes synthetic `student-mapping.csv` and `scores/anon-001.json` under `--workspace`.
- `--apply --import-only --use-existing-workspace`: reuses existing `student-mapping.csv` and `scores/*.json` and does not overwrite them.
- `--use-existing-workspace` is the recommended mode for validating real full grading artifacts imported from Python output.

## Follow-up

- Use dry-run first, then add `--apply` only when backend and database are ready.
- If the backend returns `401`, pass `--api-username` and `--api-password`.
- This script does not delete real data and does not change schema.
