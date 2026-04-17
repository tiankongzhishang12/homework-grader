import { defineStore } from "pinia";
import { taskApi } from "../api/services";
import type { ConfigBlocker, TaskDetail } from "../types";

export const useTaskContextStore = defineStore("task-context", {
  state: () => ({
    tasks: [] as TaskDetail[],
    currentTask: null as TaskDetail | null,
    blockers: [] as ConfigBlocker[],
    loading: false,
  }),
  getters: {
    currentTaskId: (state) => state.currentTask?.id ?? null,
    canStartBatch: (state) => state.blockers.length === 0,
  },
  actions: {
    async loadTasks() {
      this.loading = true;
      try {
        this.tasks = await taskApi.list();
      } finally {
        this.loading = false;
      }
    },
    async loadTask(taskId: string) {
      this.loading = true;
      try {
        this.currentTask = await taskApi.get(taskId);
        const { blockers } = await taskApi.blockers(taskId);
        this.blockers = blockers;
        const index = this.tasks.findIndex((item) => item.id === taskId);
        if (index >= 0 && this.currentTask) {
          this.tasks[index] = this.currentTask;
        }
      } finally {
        this.loading = false;
      }
    },
    async refreshBlockers(taskId?: string) {
      const target = taskId ?? this.currentTask?.id;
      if (!target) return;
      const { blockers } = await taskApi.blockers(target);
      this.blockers = blockers;
      if (this.currentTask?.id === target) {
        this.currentTask = await taskApi.get(target);
      }
    },
  },
});
