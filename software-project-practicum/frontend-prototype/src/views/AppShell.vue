<template>
  <div class="app-shell">
    <header class="mobile-appbar">
      <RouterLink :to="{ name: 'tasks' }" class="mobile-brand">
        <span class="brand__mark">HG</span>
        <span>
          <strong>智能阅卷工作台</strong>
          <small>课程驱动 · 教师优先</small>
        </span>
      </RouterLink>
      <button class="mobile-menu-button" type="button" @click="mobileNavOpen = !mobileNavOpen">
        {{ mobileNavOpen ? "收起" : "菜单" }}
      </button>
    </header>

    <div v-if="mobileNavOpen" class="mobile-nav-panel">
      <RouterLink v-for="item in globalNav" :key="item.name" :to="{ name: item.name }" class="nav__item" @click="mobileNavOpen = false">
        <span>{{ item.label }}</span>
        <small v-if="item.meta">{{ item.meta }}</small>
      </RouterLink>
      <button class="action-button action-button--ghost mobile-logout" :disabled="authStore.loading" @click="logout">退出登录</button>
    </div>
    <aside class="sidebar">
      <div class="brand">
        <div class="brand__mark">HG</div>
        <div>
          <div class="brand__title">智能阅卷工作台</div>
          <div class="brand__subtitle">课程驱动 · 教师优先</div>
        </div>
      </div>

      <nav class="nav">
        <div class="nav__group">
          <div class="nav__label">全局</div>
          <RouterLink v-for="item in globalNav" :key="item.name" :to="{ name: item.name }" class="nav__item">
            <span>{{ item.label }}</span>
            <small v-if="item.meta">{{ item.meta }}</small>
          </RouterLink>
        </div>
      </nav>

      <section v-if="taskStore.currentTask" class="sidebar-card">
        <div class="sidebar-card__label">当前任务</div>
        <div class="sidebar-card__value">{{ taskStore.currentTask.taskName }}</div>
        <div class="sidebar-card__status">{{ statusLabel }}</div>
      </section>

      <nav v-if="taskStore.currentTask" class="nav nav--task" aria-label="任务流程">
        <div class="nav__group">
          <div class="nav__label">任务流程</div>
          <RouterLink
            v-for="item in taskTabs"
            :key="item.name"
            :to="{ name: item.name, params: { taskId } }"
            class="nav__item nav__item--task"
            :class="{ 'nav__item--current': isTaskTabActive(item.name) }"
          >
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <section class="sidebar-card sidebar-card--user">
        <div class="sidebar-card__label">当前登录</div>
        <div class="sidebar-card__value">{{ authStore.user?.name }}</div>
        <div class="sidebar-card__meta">{{ authStore.user?.username }}</div>
      </section>
    </aside>

    <main class="main">
      <header class="topbar topbar--refined">
        <div class="topbar__main">
          <div class="eyebrow">{{ route.meta.title ?? "教师工作台" }}</div>
          <h1 class="page-title">{{ title }}</h1>
          <p v-if="contextSubtitle" class="topbar-subtitle">{{ contextSubtitle }}</p>
        </div>

        <div class="topbar-actions topbar-actions--refined">
          <div v-if="taskStore.currentTask" class="status-summary-card">
            <span class="status-summary-card__label">批次状态</span>
            <strong>{{ statusLabel }}</strong>
            <span class="status-summary-card__meta">
              {{ taskStore.canStartBatch ? "已满足执行条件" : `${taskStore.blockers.length} 个阻断项待处理` }}
            </span>
          </div>

          <RouterLink
            v-if="taskStore.currentTask"
            :to="{ name: 'course-workspace', params: { courseName: taskStore.currentTask.courseName } }"
            class="action-button action-button--ghost"
          >
            返回课程
          </RouterLink>
          <button class="action-button action-button--ghost" :disabled="authStore.loading" @click="logout">退出登录</button>
        </div>
      </header>

      <section v-if="taskStore.currentTask" class="task-command-bar">
        <div class="task-command-bar__main">
          <span class="task-command-bar__crumb">{{ taskStore.currentTask.courseName }} / {{ taskStore.currentTask.className }}</span>
          <strong>{{ taskStore.currentTask.taskName }}</strong>
        </div>
        <div class="task-command-bar__status">
          <span class="status-badge" :class="taskStore.canStartBatch ? 'status-badge--good' : 'status-badge--warn'">{{ statusLabel }}</span>
          <span class="task-command-bar__meta">{{ blockerText }}</span>
        </div>
      </section>

      <nav v-if="taskStore.currentTask" class="task-tab-row task-tab-row--refined" aria-label="任务阶段">
        <RouterLink
          v-for="item in taskTabs"
          :key="item.name"
          :to="{ name: item.name, params: { taskId } }"
          class="task-tab-row__item"
        >
          <span>{{ item.label }}</span>
          <small>{{ item.meta }}</small>
        </RouterLink>
      </nav>

      <RouterView />
    </main>

    <AppToastStack />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import AppToastStack from "../components/AppToastStack.vue";
import { useAuthStore } from "../stores/auth";
import { useTaskContextStore } from "../stores/task-context";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const taskStore = useTaskContextStore();
const mobileNavOpen = ref(false);

const globalNav = [{ name: "tasks", label: "课程首页", meta: "选择课程与班级" }];

const taskTabs = [
  { name: "task-config", label: "配置", meta: "Setup" },
  { name: "task-grading", label: "阅卷", meta: "Batch" },
  { name: "task-analysis", label: "分析", meta: "Review" },
  { name: "task-export", label: "导出", meta: "Export" },
];

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
    failed: "执行失败",
  };
  return map[taskStore.currentTask.batchStatus] ?? taskStore.currentTask.batchStatus;
});

const blockerText = computed(() => {
  if (!taskStore.currentTask) return "";
  return taskStore.canStartBatch ? "已满足执行条件" : `${taskStore.blockers.length} 个阻断项待处理`;
});

const contextSubtitle = computed(() => {
  if (taskStore.currentTask) {
    return `${taskStore.currentTask.courseName} · ${taskStore.currentTask.className} · ${taskStore.currentTask.taskName}`;
  }
  if (route.name === "course-workspace" && taskStore.selectedCourseSummary) {
    return `${taskStore.selectedCourseSummary.courseCode} · ${taskStore.selectedCourseSummary.term} · ${taskStore.selectedCourseSummary.classCount} 个班级`;
  }
  return "";
});

const activeTaskArea = computed(() => {
  const routeName = String(route.name ?? "");
  if (["task-config", "task-answers", "task-rubrics", "task-rubric-generator", "task-rubric-detail", "task-template", "task-workspace"].includes(routeName)) {
    return "task-config";
  }
  if (routeName === "task-grading") return "task-grading";
  if (["task-analysis", "task-student-detail"].includes(routeName)) return "task-analysis";
  if (routeName === "task-export") return "task-export";
  return "";
});

const isTaskTabActive = (name: string) => activeTaskArea.value === name;

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
