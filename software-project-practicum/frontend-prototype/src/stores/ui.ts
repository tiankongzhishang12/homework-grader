import { defineStore } from "pinia";

type ToastTone = "good" | "warn" | "risk";

type Toast = {
  id: string;
  tone: ToastTone;
  message: string;
};

export const useUiStore = defineStore("ui", {
  state: () => ({
    toasts: [] as Toast[],
    appReady: false,
  }),
  actions: {
    pushToast(message: string, tone: ToastTone = "good") {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      this.toasts.push({ id, tone, message });
      window.setTimeout(() => {
        this.toasts = this.toasts.filter((item) => item.id !== id);
      }, 3200);
    },
    markReady() {
      this.appReady = true;
    },
  },
});
