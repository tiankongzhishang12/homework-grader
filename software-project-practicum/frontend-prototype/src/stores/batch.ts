import { defineStore } from "pinia";
import { batchApi, exportApi, resultApi } from "../api/services";
import type { AnalysisSummary, BatchLog, BatchProgress, ExportRecord, StudentDetail, StudentRow } from "../types";
import { useTaskContextStore } from "./task-context";
import { useUiStore } from "./ui";

let pollTimer: number | null = null;

export const useBatchStore = defineStore("batch", {
  state: () => ({
    progress: null as BatchProgress | null,
    logs: [] as BatchLog[],
    students: [] as StudentRow[],
    analytics: null as AnalysisSummary | null,
    currentStudent: null as StudentDetail | null,
    exports: [] as ExportRecord[],
    loading: false,
    polling: false,
  }),
  actions: {
    stopPolling() {
      if (pollTimer) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }
      this.polling = false;
    },
    schedulePoll(taskId: string) {
      this.stopPolling();
      this.polling = true;
      pollTimer = window.setTimeout(async () => {
        await this.loadProgress(taskId, true);
      }, 3000);
    },
    async startBatch(taskId: string) {
      this.loading = true;
      try {
        await batchApi.start(taskId);
        useUiStore().pushToast("自动阅卷已启动，系统开始进入预处理阶段。");
        await this.loadProgress(taskId, true);
        await useTaskContextStore().loadTask(taskId);
      } finally {
        this.loading = false;
      }
    },
    async loadProgress(taskId: string, continuePolling = false) {
      this.progress = await batchApi.progress(taskId);
      if (this.progress.status === "completed" || this.progress.status === "failed") {
        this.stopPolling();
      } else if (continuePolling && document.visibilityState === "visible") {
        this.schedulePoll(taskId);
      }
      await useTaskContextStore().loadTask(taskId);
    },
    async loadLogs(taskId: string) {
      this.logs = await batchApi.logs(taskId);
    },
    async loadResults(taskId: string) {
      this.loading = true;
      try {
        const [students, analytics] = await Promise.all([resultApi.students(taskId), resultApi.analytics(taskId)]);
        this.students = students;
        this.analytics = analytics;
      } finally {
        this.loading = false;
      }
    },
    async loadStudent(studentId: string, taskId: string) {
      this.loading = true;
      try {
        this.currentStudent = await resultApi.student(studentId, taskId);
      } finally {
        this.loading = false;
      }
    },
    async loadExports(taskId: string) {
      this.exports = await exportApi.history(taskId);
    },
    async createExport(taskId: string) {
      this.loading = true;
      try {
        const record = await exportApi.start(taskId);
        this.exports = [record, ...this.exports];
        useUiStore().pushToast("Excel 导出已生成并写入导出历史。");
      } finally {
        this.loading = false;
      }
    },
  },
});
