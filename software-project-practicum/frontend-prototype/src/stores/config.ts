import { defineStore } from "pinia";
import {
  answerApi,
  assessmentApi,
  exportTemplateApi,
  gradeExportApi,
  rubricApi,
  standardAnswerApi,
  submissionApi,
  templateApi,
  workspaceApi,
} from "../api/services";
import type {
  AnswerVersion,
  ExportStartResult,
  ExportTemplate,
  GradeExportRecord,
  GradeExportPrecheck,
  Rubric,
  RubricCompileResponse,
  RubricDraft,
  StandardAnswerRecord,
  SubmissionSummary,
  SubmissionRecord,
  SubmissionUploadResult,
  WorkspaceConfig,
} from "../types";
import { useTaskContextStore } from "./task-context";
import { useUiStore } from "./ui";

const toText = (value: unknown, fallback = "") => (value === null || value === undefined ? fallback : String(value));
const standardAnswerContent = (item: StandardAnswerRecord | null | undefined) => toText(item?.answer_text ?? item?.answer_json, "");

export const useConfigStore = defineStore("config", {
  state: () => ({
    answers: [] as AnswerVersion[],
    standardAnswers: [] as StandardAnswerRecord[],
    standardAnswerDraft: "",
    rubrics: [] as Rubric[],
    currentRubric: null as Rubric | null,
    compiledRubric: null as RubricCompileResponse | null,
    rubricTeacherText: "",
    generatedDraft: null as RubricDraft | null,
    generatedDraftMeta: null as { source: "text_generated" | "rubric_copy"; copiedFromName?: string } | null,
    templates: [] as ExportTemplate[],
    currentTemplate: null as ExportTemplate | null,
    workspace: null as WorkspaceConfig | null,
    submissions: [] as SubmissionRecord[],
    submissionSummary: null as SubmissionSummary | null,
    lastUploadResult: null as SubmissionUploadResult | null,
    lastExportResult: null as ExportStartResult | null,
    exportPrecheck: null as GradeExportPrecheck | null,
    gradeExportRecords: [] as GradeExportRecord[],
    loadingExportPrecheck: false,
    loadingGradeExportRecords: false,
    loading: false,
    saving: false,
  }),
  getters: {
    hasStandardAnswer(state) {
      return state.standardAnswers.length > 0;
    },
    hasRubric(state) {
      return Boolean(state.currentRubric);
    },
    hasSubmission(state) {
      return state.submissions.length > 0;
    },
  },
  actions: {
    async loadTaskConfig(taskId: string) {
      this.loading = true;
      try {
        const taskStore = useTaskContextStore();
        const task = taskStore.currentTask ?? (await taskStore.loadTask(taskId), taskStore.currentTask);
        const assessmentId = task?.assessmentId ?? null;
        const questionId = task?.questionId ?? null;

        const [answers, rubrics, currentRubric, templates, currentTemplate, workspace, standardAnswers, submissions, submissionSummary] = await Promise.all([
          answerApi.list(taskId).catch(() => []),
          rubricApi.list().catch(() => []),
          rubricApi.binding(taskId).catch(() => null),
          exportTemplateApi.list().catch(() => []),
          exportTemplateApi.current(taskId).catch(() => null),
          workspaceApi.get(taskId).catch(() => null),
          questionId ? standardAnswerApi.list(questionId).catch(() => []) : Promise.resolve([]),
          assessmentId ? submissionApi.list(assessmentId).catch(() => []) : Promise.resolve([]),
          assessmentId ? submissionApi.summary(assessmentId).catch(() => null) : Promise.resolve(null),
        ]);

        this.answers = answers;
        this.rubrics = rubrics;
        this.currentRubric = currentRubric;
        this.templates = templates;
        this.currentTemplate = currentTemplate;
        this.workspace = workspace;
        this.standardAnswers = standardAnswers;
        this.submissions = submissions;
        this.submissionSummary = submissionSummary;
        this.standardAnswerDraft = standardAnswers[0]?.answer_text ?? "";
      } finally {
        this.loading = false;
      }
    },
    async initializeTemplateAndQuestion(taskId: string) {
      const taskStore = useTaskContextStore();
      const task = taskStore.currentTask;
      if (!task?.assessmentId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        const templateRes = await assessmentApi.createTemplate(task.assessmentId, {
          template_name: `${task.taskName} Template`,
          version_no: 1,
          status: 1,
        });
        await templateApi.createQuestion(String(templateRes.id), {
          question_no: "Q1",
          section_name: `${task.taskName} Main Question`,
          question_text: `${task.taskName} standard answer prompt`,
          sort_order: 1,
          status: 1,
        });
        await taskStore.loadTask(taskId);
        await this.loadTaskConfig(taskId);
        useUiStore().pushToast("Done.");
      } finally {
        this.saving = false;
      }
    },
    async saveStandardAnswer(taskId: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.questionId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }
      if (!this.standardAnswerDraft.trim()) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        await standardAnswerApi.create(task.questionId, {
          answer_text: this.standardAnswerDraft.trim(),
        });
        this.standardAnswers = await standardAnswerApi.list(task.questionId);
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async uploadStandardAnswerFile(taskId: string, file: File) {
      const task = useTaskContextStore().currentTask;
      if (!task?.questionId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        await standardAnswerApi.upload(task.questionId, file);
        this.standardAnswers = await standardAnswerApi.list(task.questionId);
        this.standardAnswerDraft = this.standardAnswers[0]?.answer_text ?? "";
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async uploadAnswer(taskId: string, file: File) {
      this.saving = true;
      try {
        await answerApi.upload(taskId, file);
        this.answers = await answerApi.list(taskId);
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async activateAnswer(taskId: string, versionId: string) {
      this.saving = true;
      try {
        await answerApi.activate(taskId, versionId);
        this.answers = await answerApi.list(taskId);
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async saveRubricDefinition(taskId: string, payloadText: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.templateId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }
      if (!payloadText.trim()) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        await templateApi.createRubric(task.templateId, {
          rubric_name: `${task.taskName} Rubric`,
          rubric_json: payloadText.trim(),
          status: 1,
        });
        this.currentRubric = {
          id: `template-${task.templateId}-rubric`,
          name: `${task.taskName} Rubric`,
          version: "v1.0",
          source: "manual",
          status: "confirmed",
          updatedAt: new Date().toISOString(),
          description: "Saved through real template rubric API.",
          warnings: [],
          totalScore: task.score,
          dimensions: [],
          yaml: payloadText.trim(),
        };
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async compileRubricFromText(taskId: string, teacherText: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.templateId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }
      if (!teacherText.trim()) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        this.rubricTeacherText = teacherText;
        this.compiledRubric = await rubricApi.compile(task.templateId, {
          teacherText: teacherText.trim(),
          taskName: task.taskName,
          totalScore: task.score,
          language: "zh-CN",
        });
        useUiStore().pushToast("Done.");
      } catch (error) {
        this.compiledRubric = null;
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
      } finally {
        this.saving = false;
      }
    },
    async saveCompiledRubric(taskId: string) {
      if (!this.compiledRubric) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }
      if (!this.compiledRubric.canSave) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      await this.saveRubricDefinition(taskId, JSON.stringify(this.compiledRubric.rubricJson, null, 2));
    },
    async uploadSubmission(taskId: string, studentId: string, file: File) {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }
      if (!studentId.trim()) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.saving = true;
      try {
        this.lastUploadResult = await submissionApi.upload(task.assessmentId, studentId.trim(), file);
        this.submissions = await submissionApi.list(task.assessmentId);
        this.submissionSummary = await submissionApi.summary(task.assessmentId).catch(() => null);
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async loadSubmissionSummary(taskId: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) return;
      this.submissionSummary = await submissionApi.summary(task.assessmentId);
      this.submissions = await submissionApi.list(task.assessmentId);
      await useTaskContextStore().refreshBlockers(taskId);
    },
    async saveTemplate(taskId: string, template: ExportTemplate) {
      this.saving = true;
      try {
        if (template.id.startsWith("template-")) {
          this.currentTemplate = await exportTemplateApi.update(template.id, template);
        } else {
          this.currentTemplate = await exportTemplateApi.create(template);
        }
        this.templates = await exportTemplateApi.list();
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async bindTemplate(taskId: string, templateId: string) {
      this.saving = true;
      try {
        await exportTemplateApi.bind(taskId, templateId);
        this.currentTemplate = await exportTemplateApi.current(taskId);
        this.templates = await exportTemplateApi.list();
        useUiStore().pushToast("Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async checkWorkspace(taskId: string) {
      this.saving = true;
      try {
        this.workspace = await workspaceApi.check(taskId);
        useUiStore().pushToast(this.workspace.lastMessage ?? "Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async initWorkspace(taskId: string) {
      this.saving = true;
      try {
        this.workspace = await workspaceApi.init(taskId);
        useUiStore().pushToast(this.workspace.lastMessage ?? "Done.");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async loadGradeExportPrecheck(taskId: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) {
        this.exportPrecheck = null;
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return;
      }

      this.loadingExportPrecheck = true;
      try {
        this.exportPrecheck = await gradeExportApi.precheck(task.assessmentId);
      } catch (error) {
        this.exportPrecheck = null;
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
      } finally {
        this.loadingExportPrecheck = false;
      }
      void taskId;
    },
    async loadGradeExportRecords(taskId: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) {
        this.gradeExportRecords = [];
        return;
      }

      this.loadingGradeExportRecords = true;
      try {
        this.gradeExportRecords = await gradeExportApi.list(task.assessmentId);
      } catch (error) {
        this.gradeExportRecords = [];
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
      } finally {
        this.loadingGradeExportRecords = false;
      }
      void taskId;
    },
    async startGradeExport() {
      const taskStore = useTaskContextStore();
      const task = taskStore.currentTask;
      if (!task?.assessmentId) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return null;
      }

      this.saving = true;
      try {
        this.lastExportResult = await gradeExportApi.start(task.assessmentId);
        await this.loadGradeExportRecords(task.id);
        await this.loadGradeExportPrecheck(task.id);
        if (this.lastExportResult.status === "FAILED") {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        } else {
          const idPart = this.lastExportResult.exportId ? " (record #" + this.lastExportResult.exportId + ")" : "";
          useUiStore().pushToast(this.lastExportResult.report ? "Export completed: " + this.lastExportResult.report + idPart : "Export started" + idPart + ".");
        }
        return this.lastExportResult;
      } catch (error) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
        return null;
      } finally {
        this.saving = false;
      }
    },
    async downloadLatestReport() {
      this.saving = true;
      try {
        const blob = await gradeExportApi.downloadLatest();
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "latest-report.xlsx";
        anchor.click();
        window.URL.revokeObjectURL(url);
        useUiStore().pushToast("Done.");
      } catch (error) {
        useUiStore().pushToast("Operation failed. Please check configuration or backend API.", "risk");
      } finally {
        this.saving = false;
      }
    },
    configChecklist(taskId: string) {
      const taskStore = useTaskContextStore();
      const task = taskStore.currentTask;
      const items = [
        { id: "assessment", ok: Boolean(task?.assessmentId), label: "assessmentId" },
        { id: "template", ok: Boolean(task?.templateId), label: "templateId" },
        { id: "question", ok: Boolean(task?.questionId), label: "questionId" },
        { id: "answer", ok: this.standardAnswers.length > 0 || this.answers.length > 0, label: "standard answer" },
        { id: "rubric", ok: Boolean(this.currentRubric), label: "Rubric" },
        { id: "submission", ok: this.submissions.length > 0, label: "student submission" },
      ];
      const missing = items.filter((item) => !item.ok).map((item) => item.label);
      return {
        ready: missing.length === 0,
        missing,
        message: missing.length === 0 ? "Configuration is ready." : "Missing before grading: " + missing.join(", "),
        taskId,
      };
    },
    summarizeLatestUpload() {
      if (!this.lastUploadResult) return "";
      const raw = this.lastUploadResult.rawWorkspace;
      if (!raw) return "";
      return [raw.synced ? "raw workspace synced" : "raw workspace not synced", raw.path, raw.message]
        .filter(Boolean)
        .join(" | ");
    },
    summarizeStandardAnswer() {
      if (this.standardAnswers.length > 0) {
        const item = this.standardAnswers[0];
        return item.answer_text ? String(toText(item.answer_text).slice(0, 120)) : "Standard answer record " + item.id;
      }
      return "No standard answer records.";
    },
    getLatestStandardAnswer() {
      return this.standardAnswers[0] ?? null;
    },
    formatStandardAnswerSummary(item: StandardAnswerRecord | null | undefined, maxLength = 120) {
      const text = standardAnswerContent(item).trim() || "No text content";
      return text.length > maxLength ? text.slice(0, maxLength) + "..." : text;
    },
    formatStandardAnswerVersion(item: StandardAnswerRecord | null | undefined) {
      if (!item) return "None";
      return item.version_no ? "v" + item.version_no : "#" + item.id;
    },
    formatFileSize(size: number) {
      if (size >= 1024 * 1024) return (size / 1024 / 1024).toFixed(2) + " MB";
      return Math.max(size / 1024, 0.01).toFixed(2) + " KB";
    },
  },
});
