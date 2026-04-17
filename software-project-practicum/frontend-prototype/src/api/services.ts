import { apiRequest } from "./client";
import type {
  AnalysisSummary,
  AnswerVersion,
  BatchLog,
  BatchProgress,
  ConfigBlocker,
  ExportRecord,
  ExportTemplate,
  Rubric,
  RubricDraft,
  StudentDetail,
  StudentRow,
  TaskDetail,
  User,
  WorkspaceConfig,
} from "../types";

export const authApi = {
  login: (payload: { username: string; password: string }) =>
    apiRequest<User>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => apiRequest<User>("/api/auth/me"),
  logout: () => apiRequest<{ success: boolean }>("/api/auth/logout", { method: "POST" }),
};

export const taskApi = {
  list: () => apiRequest<TaskDetail[]>("/api/tasks"),
  get: (taskId: string) => apiRequest<TaskDetail>(`/api/tasks/${taskId}`),
  blockers: (taskId: string) => apiRequest<{ blockers: ConfigBlocker[] }>(`/api/tasks/${taskId}/config-status`),
};

export const answerApi = {
  list: (taskId: string) => apiRequest<AnswerVersion[]>(`/api/tasks/${taskId}/answers`),
  upload: (taskId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<AnswerVersion>(`/api/tasks/${taskId}/answers`, { method: "POST", body: form });
  },
  get: (taskId: string, versionId: string) => apiRequest<AnswerVersion>(`/api/tasks/${taskId}/answers/${versionId}`),
  activate: (taskId: string, versionId: string) =>
    apiRequest<{ success: boolean }>(`/api/tasks/${taskId}/answers/${versionId}/activate`, { method: "POST" }),
};

export const rubricApi = {
  list: () => apiRequest<Rubric[]>("/api/rubrics"),
  binding: (taskId: string) => apiRequest<Rubric>(`/api/tasks/${taskId}/rubric-binding`),
  generate: (payload: { prompt: string }) =>
    apiRequest<RubricDraft>("/api/rubrics/generate", { method: "POST", body: JSON.stringify(payload) }),
  create: (payload: Rubric) => apiRequest<Rubric>("/api/rubrics", { method: "POST", body: JSON.stringify(payload) }),
  update: (rubricId: string, payload: Partial<Rubric>) =>
    apiRequest<Rubric>(`/api/rubrics/${rubricId}`, { method: "PUT", body: JSON.stringify(payload) }),
  bind: (taskId: string, rubricId: string) =>
    apiRequest<{ success: boolean }>(`/api/tasks/${taskId}/rubric-binding`, {
      method: "POST",
      body: JSON.stringify({ rubricId }),
    }),
};

export const exportTemplateApi = {
  list: () => apiRequest<ExportTemplate[]>("/api/export-templates"),
  current: (taskId: string) => apiRequest<ExportTemplate>(`/api/tasks/${taskId}/export-template`),
  create: (payload: ExportTemplate) =>
    apiRequest<ExportTemplate>("/api/export-templates", { method: "POST", body: JSON.stringify(payload) }),
  update: (templateId: string, payload: Partial<ExportTemplate>) =>
    apiRequest<ExportTemplate>(`/api/export-templates/${templateId}`, { method: "PUT", body: JSON.stringify(payload) }),
  bind: (taskId: string, templateId: string) =>
    apiRequest<{ success: boolean }>(`/api/tasks/${taskId}/export-template/bind`, {
      method: "POST",
      body: JSON.stringify({ templateId }),
    }),
};

export const workspaceApi = {
  get: (taskId: string) => apiRequest<WorkspaceConfig>(`/api/tasks/${taskId}/workspace`),
  check: (taskId: string) => apiRequest<WorkspaceConfig>(`/api/tasks/${taskId}/workspace/check`, { method: "POST" }),
  init: (taskId: string) => apiRequest<WorkspaceConfig>(`/api/tasks/${taskId}/workspace/init`, { method: "POST" }),
};

export const batchApi = {
  start: (taskId: string) =>
    apiRequest<{ success: boolean }>("/api/batch/start", { method: "POST", body: JSON.stringify({ taskId }) }),
  progress: (taskId: string) => apiRequest<BatchProgress>(`/api/batch/progress?taskId=${taskId}`),
  logs: (taskId: string) => apiRequest<BatchLog[]>(`/api/batch/logs?taskId=${taskId}`),
};

export const resultApi = {
  students: (taskId: string) => apiRequest<StudentRow[]>(`/api/students?taskId=${taskId}`),
  student: (studentId: string, taskId: string) => apiRequest<StudentDetail>(`/api/students/${studentId}?taskId=${taskId}`),
  analytics: (taskId: string) => apiRequest<AnalysisSummary>(`/api/analytics?taskId=${taskId}`),
};

export const exportApi = {
  start: (taskId: string) =>
    apiRequest<ExportRecord>("/api/batch/export", { method: "POST", body: JSON.stringify({ taskId }) }),
  history: (taskId: string) => apiRequest<ExportRecord[]>(`/api/exports?taskId=${taskId}`),
};
