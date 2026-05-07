# Frontend Architecture

## Source Of Truth

Frontend code lives in `software-project-practicum/frontend-prototype/`.

Current `package.json`:

- Vue `^3.5.13`
- Vue Router `^4.5.1`
- Pinia `^3.0.4`
- TypeScript `^5.8.3`
- Vite `^6.3.5`

## Main Files

- `src/main.ts`: app entry.
- `src/App.vue`: root component.
- `src/router.ts`: route tree and auth guard.
- `src/api/client.ts`: API request layer and unauthorized handler.
- `src/api/services.ts`: typed API client groups.
- `src/stores/`: Pinia stores for auth, batch, config, task context, UI, and shared pinia instance.
- `src/views/`: teacher workspace pages.
- `src/components/AppToastStack.vue`: shared toast display.
- `src/types.ts`: shared frontend types.
- `src/mock-data.ts` and `src/api/mock-server.ts`: prototype/mock support.

## Product Shape

The frontend is a teacher workspace, not a landing page. It should prioritize:

- course and task navigation;
- configuration completeness;
- Rubric and standard answer management;
- batch grading progress and logs;
- score distribution and result analysis;
- student-level evidence and comments;
- export history and downloadable artifacts.

## API Clients

`src/api/services.ts` groups client calls:

- `authApi`: login, current user, logout.
- `taskApi`: task list, task detail, config blockers.
- `answerApi`: answer versions, upload, get, activate.
- `rubricApi`: list, binding, generate, create, update, remove, bind.
- `exportTemplateApi`: list, current, create, update, bind.
- `workspaceApi`: get, check, init.
- `batchApi`: start, progress, logs.
- `resultApi`: students, student detail, analytics.
- `exportApi`: start export, history.

Some client calls may be ahead of current backend endpoints. Before building UI around a call, confirm `backend-api-map.md` or inspect backend controllers.

## Auth Flow

`router.ts` restores auth state before protected navigation. Public route:

- `/login`

All child routes under `/` require authentication. Unauthorized API responses clear session and redirect to login with a `redirect` query.

## Encoding Note

Several `meta.title` strings in `src/router.ts` appear mojibake in the current source. Treat route path, name, and component binding as source of truth. Fixing display encoding should be a deliberate task, not incidental churn.
