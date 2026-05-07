# Frontend Route Map

Generated from `software-project-practicum/frontend-prototype/src/router.ts`.

## Public Route

| Path | Name | Component |
| --- | --- | --- |
| `/login` | `login` | `LoginView` |

## Authenticated Shell

Parent route `/` renders `AppShell` and requires auth.

| Path | Name | Component / Behavior |
| --- | --- | --- |
| `/` | - | redirects to `/tasks` |
| `/tasks` | `tasks` | `TaskListView` |
| `/courses/:courseName` | `course-workspace` | `CourseWorkspaceView` |
| `/tasks/:taskId` | - | redirects to `/tasks/:taskId/config` |
| `/tasks/:taskId/config` | `task-config` | `TaskConfigView` |
| `/tasks/:taskId/config/answers` | `task-answers` | `StandardAnswersView` |
| `/tasks/:taskId/rubrics` | `task-rubrics` | `RubricManagementView` |
| `/tasks/:taskId/rubrics/generate` | `task-rubric-generator` | `RubricGeneratorView` |
| `/tasks/:taskId/rubrics/:rubricId` | `task-rubric-detail` | `RubricDetailView` |
| `/tasks/:taskId/config/template` | `task-template` | `ExportTemplateView` |
| `/tasks/:taskId/config/workspace` | `task-workspace` | `WorkspaceSettingsView` |
| `/tasks/:taskId/grading` | `task-grading` | `BatchGradingView` |
| `/tasks/:taskId/analysis` | `task-analysis` | `ResultAnalysisView` |
| `/tasks/:taskId/students/:studentId` | `task-student-detail` | `StudentDetailView` |
| `/tasks/:taskId/export` | `task-export` | `ExportCenterView` |

## Imported But Not Routed In Current Router

These view files exist under `src/views/` but are not currently wired in `router.ts`:

- `AssignmentDetailView.vue`
- `CourseTasksView.vue`
- `DashboardView.vue`
- `ScoringRulesView.vue`
- `StudentListView.vue`
- `TaskCenterView.vue`
- `TeachingClassesView.vue`

Do not invent routes for these views without checking the intended navigation model.
