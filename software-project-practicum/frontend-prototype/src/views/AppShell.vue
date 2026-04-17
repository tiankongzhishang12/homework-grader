<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand__mark">SP</div>
        <div>
          <div class="brand__title">智能阅卷工作台</div>
          <div class="brand__subtitle">教师单端 · 桌面优先</div>
        </div>
      </div>

      <nav class="nav">
        <div class="nav__group">
          <div class="nav__label">全局入口</div>
          <RouterLink :to="{ name: 'tasks' }" class="nav__item">任务列表</RouterLink>
        </div>

        <div v-if="taskStore.currentTask" class="nav__group">
          <div class="nav__label">当前任务</div>
          <RouterLink :to="{ name: 'task-config', params: { taskId: taskId } }" class="nav__item">任务配置</RouterLink>
          <RouterLink :to="{ name: 'task-answers', params: { taskId: taskId } }" class="nav__item">标准答案</RouterLink>
          <RouterLink :to="{ name: 'task-rubrics', params: { taskId: taskId } }" class="nav__item">评分标准</RouterLink>
          <RouterLink :to="{ name: 'task-template', params: { taskId: taskId } }" class="nav__item">Excel 模板</RouterLink>
          <RouterLink :to="{ name: 'task-workspace', params: { taskId: taskId } }" class="nav__item">路径配置</RouterLink>
          <RouterLink :to="{ name: 'task-grading', params: { taskId: taskId } }" class="nav__item">批量阅卷</RouterLink>
          <RouterLink :to="{ name: 'task-analysis', params: { taskId: taskId } }" class="nav__item">结果分析</RouterLink>
          <RouterLink :to="{ name: 'task-export', params: { taskId: taskId } }" class="nav__item">导出中心</RouterLink>
        </div>
      </nav>

      <section class="sidebar-card">
        <div class="sidebar-card__label">当前登录</div>
        <div class="sidebar-card__value">{{ authStore.user?.name }}</div>
        <div class="sidebar-card__meta">{{ authStore.user?.username }}</div>
      </section>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <div class="eyebrow">{{ route.meta.title ?? "教师工作台" }}</div>
          <h1 class="page-title">{{ title }}</h1>
          <p v-if="taskStore.currentTask" class="topbar-subtitle">
            {{ taskStore.currentTask.courseName }} · {{ taskStore.currentTask.className }} · {{ taskStore.currentTask.taskName }}
          </p>
        </div>

        <div class="topbar-actions">
          <span v-if="taskStore.currentTask" class="pill" :class="taskStore.canStartBatch ? 'pill--good' : 'pill--warn'">
            {{ taskStore.canStartBatch ? "配置已就绪" : `${taskStore.blockers.length} 项阻断` }}
          </span>
          <span v-if="taskStore.currentTask" class="pill">{{ statusLabel }}</span>
          <button class="action-button action-button--ghost" :disabled="authStore.loading" @click="logout">退出登录</button>
        </div>
      </header>

      <div v-if="taskStore.currentTask" class="task-tab-row">
        <RouterLink :to="{ name: 'task-config', params: { taskId: taskId } }" class="task-tab-row__item">配置总览</RouterLink>
        <RouterLink :to="{ name: 'task-grading', params: { taskId: taskId } }" class="task-tab-row__item">批量阅卷</RouterLink>
        <RouterLink :to="{ name: 'task-analysis', params: { taskId: taskId } }" class="task-tab-row__item">结果分析</RouterLink>
        <RouterLink :to="{ name: 'task-export', params: { taskId: taskId } }" class="task-tab-row__item">导出中心</RouterLink>
      </div>

      <RouterView />
    </main>

    <AppToastStack />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import AppToastStack from "../components/AppToastStack.vue";
import { useAuthStore } from "../stores/auth";
import { useTaskContextStore } from "../stores/task-context";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const taskStore = useTaskContextStore();

const taskId = computed(() => String(route.params.taskId ?? ""));

const title = computed(() => (route.meta.title as string | undefined) ?? "教师工作台");
const statusLabel = computed(() => {
  if (!taskStore.currentTask) return "";
  const map: Record<string, string> = {
    idle: "待开始",
    preprocessing: "预处理中",
    scoring: "评分中",
    aggregating: "汇总中",
    completed: "已完成",
    failed: "失败",
  };
  return `批次状态：${map[taskStore.currentTask.batchStatus] ?? taskStore.currentTask.batchStatus}`;
});

const syncTask = async () => {
  if (route.params.taskId) {
    await taskStore.loadTask(taskId.value);
  } else {
    taskStore.currentTask = null;
    taskStore.blockers = [];
  }
};

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await taskStore.loadTasks();
    await syncTask();
  }
});

watch(
  () => route.params.taskId,
  async () => {
    await syncTask();
  },
);

const logout = async () => {
  await authStore.logout();
  await router.push({ name: "login" });
};
</script>
