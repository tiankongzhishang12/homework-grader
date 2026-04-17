import { createRouter, createWebHistory } from "vue-router";
import { pinia } from "./stores/pinia";
import { useAuthStore } from "./stores/auth";
import AppShell from "./views/AppShell.vue";
import LoginView from "./views/LoginView.vue";
import TaskListView from "./views/TaskListView.vue";
import TaskConfigView from "./views/TaskConfigView.vue";
import StandardAnswersView from "./views/StandardAnswersView.vue";
import RubricManagementView from "./views/RubricManagementView.vue";
import RubricGeneratorView from "./views/RubricGeneratorView.vue";
import ExportTemplateView from "./views/ExportTemplateView.vue";
import WorkspaceSettingsView from "./views/WorkspaceSettingsView.vue";
import BatchGradingView from "./views/BatchGradingView.vue";
import ResultAnalysisView from "./views/ResultAnalysisView.vue";
import StudentDetailView from "./views/StudentDetailView.vue";
import ExportCenterView from "./views/ExportCenterView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true, title: "教师登录" } },
    {
      path: "/",
      component: AppShell,
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/tasks" },
        { path: "tasks", name: "tasks", component: TaskListView, meta: { title: "任务列表" } },
        { path: "tasks/:taskId", redirect: (to) => `/tasks/${to.params.taskId}/config` },
        { path: "tasks/:taskId/config", name: "task-config", component: TaskConfigView, meta: { title: "任务配置" } },
        { path: "tasks/:taskId/config/answers", name: "task-answers", component: StandardAnswersView, meta: { title: "标准答案设置" } },
        { path: "tasks/:taskId/rubrics", name: "task-rubrics", component: RubricManagementView, meta: { title: "评分标准配置" } },
        { path: "tasks/:taskId/rubrics/generate", name: "task-rubric-generator", component: RubricGeneratorView, meta: { title: "文本生成 Rubric" } },
        { path: "tasks/:taskId/config/template", name: "task-template", component: ExportTemplateView, meta: { title: "Excel 结果表格式设置" } },
        { path: "tasks/:taskId/config/workspace", name: "task-workspace", component: WorkspaceSettingsView, meta: { title: "批量阅卷路径配置" } },
        { path: "tasks/:taskId/grading", name: "task-grading", component: BatchGradingView, meta: { title: "批量阅卷" } },
        { path: "tasks/:taskId/analysis", name: "task-analysis", component: ResultAnalysisView, meta: { title: "结果分析" } },
        { path: "tasks/:taskId/students/:studentId", name: "task-student-detail", component: StudentDetailView, meta: { title: "样本解释" } },
        { path: "tasks/:taskId/export", name: "task-export", component: ExportCenterView, meta: { title: "导出中心" } },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);
  if (!authStore.initialized) {
    await authStore.restoreSession();
  }
  if (to.meta.public) {
    if (authStore.isAuthenticated && to.name === "login") {
      return { name: "tasks" };
    }
    return true;
  }
  if (!authStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
