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
        useUiStore().pushToast("当前任务缺少 assessmentId，无法初始化题目定义。", "risk");
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
        useUiStore().pushToast("assessment template 和 question definition 已初始化。");
      } finally {
        this.saving = false;
      }
    },
    async saveStandardAnswer(taskId: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.questionId) {
        useUiStore().pushToast("请先初始化题目定义。", "risk");
        return;
      }
      if (!this.standardAnswerDraft.trim()) {
        useUiStore().pushToast("请先输入标准答案文本。", "risk");
        return;
      }

      this.saving = true;
      try {
        await standardAnswerApi.create(task.questionId, {
          answer_text: this.standardAnswerDraft.trim(),
        });
        this.standardAnswers = await standardAnswerApi.list(task.questionId);
        useUiStore().pushToast("标准答案文本已保存为新版本。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async uploadStandardAnswerFile(taskId: string, file: File) {
      const task = useTaskContextStore().currentTask;
      if (!task?.questionId) {
        useUiStore().pushToast("请先初始化题目定义。", "risk");
        return;
      }

      this.saving = true;
      try {
        await standardAnswerApi.upload(task.questionId, file);
        this.standardAnswers = await standardAnswerApi.list(task.questionId);
        this.standardAnswerDraft = this.standardAnswers[0]?.answer_text ?? "";
        useUiStore().pushToast("标准答案文件已上传并保存为新版本。");
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
        useUiStore().pushToast("标准答案文件已上传，系统正在解析。");
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
        useUiStore().pushToast("标准答案版本已切换为当前使用版本。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async saveRubricDefinition(taskId: string, payloadText: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.templateId) {
        useUiStore().pushToast("请先初始化 assessment template。", "risk");
        return;
      }
      if (!payloadText.trim()) {
        useUiStore().pushToast("请先输入 Rubric JSON 或 YAML。", "risk");
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
        useUiStore().pushToast("Rubric 已保存到真实后端接口。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async compileRubricFromText(taskId: string, teacherText: string) {
      const task = useTaskContextStore().currentTask;
      if (!task?.templateId) {
        useUiStore().pushToast("请先初始化 assessment template，再生成评分标准。", "risk");
        return;
      }
      if (!teacherText.trim()) {
        useUiStore().pushToast("请先输入中文评分标准。", "risk");
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
        useUiStore().pushToast("结构化评分标准草稿已生成。");
      } catch (error) {
        this.compiledRubric = null;
        useUiStore().pushToast("评分标准生成失败，请检查模型配置或稍后重试。", "risk");
      } finally {
        this.saving = false;
      }
    },
    async saveCompiledRubric(taskId: string) {
      if (!this.compiledRubric) {
        useUiStore().pushToast("请先生成评分标准草稿。", "risk");
        return;
      }
      if (!this.compiledRubric.canSave) {
        useUiStore().pushToast("当前草稿存在风险，请根据提示修改后重新生成。", "risk");
        return;
      }

      await this.saveRubricDefinition(taskId, JSON.stringify(this.compiledRubric.rubricJson, null, 2));
    },
    async uploadSubmission(taskId: string, studentId: string, file: File) {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) {
        useUiStore().pushToast("当前任务缺少 assessmentId，无法上传学生作业。", "risk");
        return;
      }
      if (!studentId.trim()) {
        useUiStore().pushToast("请先输入 studentId。", "risk");
        return;
      }

      this.saving = true;
      try {
        this.lastUploadResult = await submissionApi.upload(task.assessmentId, studentId.trim(), file);
        this.submissions = await submissionApi.list(task.assessmentId);
        this.submissionSummary = await submissionApi.summary(task.assessmentId).catch(() => null);
        useUiStore().pushToast(this.lastUploadResult.message ?? "作业上传成功，已加入待批改队列。", "good");
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
        useUiStore().pushToast("Excel 模板已保存。");
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
        useUiStore().pushToast("Excel 模板已绑定到当前任务。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async checkWorkspace(taskId: string) {
      this.saving = true;
      try {
        this.workspace = await workspaceApi.check(taskId);
        useUiStore().pushToast(this.workspace.lastMessage ?? "路径检测完成。", this.workspace.status === "valid" ? "good" : "warn");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async initWorkspace(taskId: string) {
      this.saving = true;
      try {
        this.workspace = await workspaceApi.init(taskId);
        useUiStore().pushToast(this.workspace.lastMessage ?? "目录初始化完成。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async startGradeExport() {
      const task = useTaskContextStore().currentTask;
      if (!task?.assessmentId) {
        useUiStore().pushToast("当前任务缺少 assessmentId，无法导出成绩。", "risk");
        return null;
      }

      this.saving = true;
      try {
        this.lastExportResult = await gradeExportApi.start(task.assessmentId);
        useUiStore().pushToast(
          this.lastExportResult.report ? `成绩导出已触发：${this.lastExportResult.report}` : "成绩导出已触发。",
        );
        return this.lastExportResult;
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
        useUiStore().pushToast("最新报表下载已开始。");
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
        { id: "answer", ok: this.standardAnswers.length > 0 || this.answers.length > 0, label: "标准答案" },
        { id: "rubric", ok: Boolean(this.currentRubric), label: "Rubric" },
        { id: "submission", ok: this.submissions.length > 0, label: "学生提交" },
      ];
      const missing = items.filter((item) => !item.ok).map((item) => item.label);
      return {
        ready: missing.length === 0,
        missing,
        message: missing.length === 0 ? "配置已满足开始阅卷条件。" : `开始阅卷前仍缺少：${missing.join("、")}`,
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
        return item.answer_text ? `${toText(item.answer_text).slice(0, 120)}` : `标准答案记录 ${item.id}`;
      }
      return "暂无真实标准答案记录。";
    },
    getLatestStandardAnswer() {
      return this.standardAnswers[0] ?? null;
    },
    formatStandardAnswerSummary(item: StandardAnswerRecord | null | undefined, maxLength = 120) {
      const text = standardAnswerContent(item).trim() || "无文本内容";
      return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
    },
    formatStandardAnswerVersion(item: StandardAnswerRecord | null | undefined) {
      if (!item) return "暂无";
      return item.version_no ? `v${item.version_no}` : `#${item.id}`;
    },
    formatFileSize(size: number) {
      if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`;
      return `${Math.max(size / 1024, 0.01).toFixed(2)} KB`;
    },
  },
});
