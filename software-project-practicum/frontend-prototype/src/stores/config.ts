import { defineStore } from "pinia";
import { answerApi, exportTemplateApi, rubricApi, workspaceApi } from "../api/services";
import type { AnswerVersion, ExportTemplate, Rubric, RubricDraft, WorkspaceConfig } from "../types";
import { useTaskContextStore } from "./task-context";
import { useUiStore } from "./ui";

export const useConfigStore = defineStore("config", {
  state: () => ({
    answers: [] as AnswerVersion[],
    rubrics: [] as Rubric[],
    currentRubric: null as Rubric | null,
    generatedDraft: null as RubricDraft | null,
    generatedDraftMeta: null as { source: "text_generated" | "rubric_copy"; copiedFromName?: string } | null,
    templates: [] as ExportTemplate[],
    currentTemplate: null as ExportTemplate | null,
    workspace: null as WorkspaceConfig | null,
    loading: false,
    saving: false,
  }),
  actions: {
    async loadTaskConfig(taskId: string) {
      this.loading = true;
      try {
        const [answers, rubrics, currentRubric, templates, currentTemplate, workspace] = await Promise.all([
          answerApi.list(taskId),
          rubricApi.list(),
          rubricApi.binding(taskId).catch(() => null),
          exportTemplateApi.list(),
          exportTemplateApi.current(taskId).catch(() => null),
          workspaceApi.get(taskId).catch(() => null),
        ]);
        this.answers = answers;
        this.rubrics = rubrics;
        this.currentRubric = currentRubric;
        this.templates = templates;
        this.currentTemplate = currentTemplate;
        this.workspace = workspace;
      } finally {
        this.loading = false;
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
    async generateRubric(prompt: string, baseRubric?: Rubric | null) {
      this.saving = true;
      try {
        const normalizedPrompt = [
          prompt,
          /100/.test(prompt) ? "" : "总分 100 分。",
          /门禁/.test(prompt) ? "" : "请补充明确的门禁规则。",
        ]
          .filter(Boolean)
          .join("\n");
        this.generatedDraft = await rubricApi.generate({ prompt: normalizedPrompt, baseRubricId: baseRubric?.id ?? null });
        this.generatedDraftMeta = baseRubric
          ? { source: "rubric_copy", copiedFromName: `${baseRubric.name} ${baseRubric.version}` }
          : { source: "text_generated" };
      } finally {
        this.saving = false;
      }
    },
    resetGeneratedDraft() {
      this.generatedDraft = null;
      this.generatedDraftMeta = null;
    },
    async saveGeneratedRubric(taskId: string, bindable = false) {
      if (!this.generatedDraft) return null;
      this.saving = true;
      try {
        const created = await rubricApi.create({
          id: "",
          name: this.generatedDraft.name,
          version: "v0.1",
          source: this.generatedDraftMeta?.source ?? "text_generated",
          status: bindable ? "confirmed" : "draft",
          updatedAt: "",
          description: this.generatedDraft.description,
          warnings: this.generatedDraft.warnings,
          totalScore: this.generatedDraft.totalScore,
          dimensions: this.generatedDraft.dimensions,
          yaml: this.generatedDraft.yaml,
          createdAt: new Date().toLocaleString("zh-CN", { hour12: false }).replace(/\//g, "-"),
          copiedFromName: this.generatedDraftMeta?.copiedFromName,
          editCount: 0,
        });
        this.rubrics = await rubricApi.list();
        this.currentRubric = created;
        this.resetGeneratedDraft();
        useUiStore().pushToast(
          created.source === "rubric_copy" ? "已基于现有标准生成草稿副本。" : "文本生成的 Rubric 已保存为草稿。",
        );
        await useTaskContextStore().refreshBlockers(taskId);
        return created;
      } finally {
        this.saving = false;
      }
    },
    async bindRubric(taskId: string, rubricId: string) {
      this.saving = true;
      try {
        await rubricApi.bind(taskId, rubricId);
        this.currentRubric = await rubricApi.binding(taskId);
        this.rubrics = await rubricApi.list();
        useUiStore().pushToast("评分标准已绑定到当前任务。");
        await useTaskContextStore().refreshBlockers(taskId);
      } finally {
        this.saving = false;
      }
    },
    async deleteRubricCopy(rubricId: string) {
      this.saving = true;
      try {
        await rubricApi.remove(rubricId);
        this.rubrics = await rubricApi.list();
        if (this.currentRubric?.id === rubricId) {
          this.currentRubric = null;
        }
        useUiStore().pushToast("评分标准副本已删除。");
      } finally {
        this.saving = false;
      }
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
  },
});
