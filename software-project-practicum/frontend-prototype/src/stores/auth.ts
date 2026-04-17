import { defineStore } from "pinia";
import { authApi } from "../api/services";
import type { User } from "../types";
import { useUiStore } from "./ui";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as User | null,
    loading: false,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
  },
  actions: {
    async restoreSession() {
      if (this.initialized) return;
      this.loading = true;
      try {
        this.user = await authApi.me();
      } catch {
        this.user = null;
      } finally {
        this.loading = false;
        this.initialized = true;
      }
    },
    async login(username: string, password: string) {
      this.loading = true;
      try {
        this.user = await authApi.login({ username, password });
        useUiStore().pushToast("登录成功，已进入教师工作台。");
      } finally {
        this.loading = false;
        this.initialized = true;
      }
    },
    async logout() {
      this.loading = true;
      try {
        await authApi.logout();
        this.user = null;
      } finally {
        this.loading = false;
      }
    },
  },
});
