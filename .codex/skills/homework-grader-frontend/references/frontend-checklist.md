# Frontend Checklist

## Before Editing

- Read `src/router.ts` for route names and params.
- Check `src/api/services.ts` for available client calls.
- Check relevant Pinia store under `src/stores/`.
- Inspect the target view under `src/views/`.
- For backend-dependent UI, verify the controller endpoint exists.

## UI Rules

- Build teacher workspace screens, not marketing pages.
- Keep task status, grading progress, evidence, confidence, review state, and export state visible where relevant.
- Avoid hiding teacher review actions behind unclear text.
- Preserve route params such as `taskId`, `rubricId`, and `studentId`.
- Keep empty, loading, error, unauthorized, and partial-data states clear.

## Verification

- Run `npm run build` from `software-project-practicum/frontend-prototype` for frontend changes when feasible.
- If UI behavior changes, test in browser against Vite dev server or backend API.
- Confirm no route introduced in docs exists only in imagination; `router.ts` is source of truth.

## Output Notes

Report frontend files changed, route/API impacts, backend assumptions, and checks run.
