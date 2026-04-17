<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">任务配置总览</div>
        <h2 class="hero-card__title">六个正式配置模块全部就绪后，才能开始自动阅卷</h2>
        <p class="hero-card__text">
          配置页聚合当前任务的班级名单、任务信息、标准答案、评分标准、Excel 模板和批量阅卷路径。所有阻断项会在顶部明确列出，避免老师误点开始阅卷。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill" :class="taskStore.canStartBatch ? 'pill--good' : 'pill--warn'">
          {{ taskStore.canStartBatch ? "可开始阅卷" : "当前不可开始" }}
        </span>
        <span class="pill">{{ taskStore.currentTask.configProgress }}% 已完成</span>
      </div>
    </div>

    <section v-if="taskStore.blockers.length > 0" class="panel panel--risk">
      <div class="panel__header">
        <h3>开始阅卷阻断项</h3>
      </div>
      <div class="issue-stack">
        <article v-for="item in taskStore.blockers" :key="item.id" class="issue-card issue-card--risk">
          <div class="issue-card__title">{{ item.title }}</div>
          <div class="issue-card__detail">{{ item.detail }}</div>
        </article>
      </div>
    </section>

    <div class="stats-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">学生人数</div>
        <div class="stat-card__value">{{ taskStore.currentTask.studentCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">已提交人数</div>
        <div class="stat-card__value">{{ taskStore.currentTask.submittedCount }}</div>
      </article>
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">任务满分</div>
        <div class="stat-card__value">{{ taskStore.currentTask.score }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">截止时间</div>
        <div class="stat-card__value stat-card__value--small">{{ taskStore.currentTask.deadline }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>配置模块</h3>
          <p class="panel__description">每个模块都给出当前状态、主要信息和直接进入页。</p>
        </div>
        <button class="action-button" :disabled="!taskStore.canStartBatch" @click="goToGrading">开始阅卷</button>
      </div>

      <div class="module-grid">
        <article class="module-card">
          <div class="module-card__top">
            <strong>教学班级与学生名单</strong>
            <span class="status-badge status-badge--good">已同步</span>
          </div>
          <p>{{ taskStore.currentTask.className }} · {{ taskStore.currentTask.studentCount }} 人，已提交 {{ taskStore.currentTask.submittedCount }} 人。</p>
        </article>

        <article class="module-card">
          <div class="module-card__top">
            <strong>课程任务信息</strong>
            <span class="status-badge status-badge--good">已确认</span>
          </div>
          <p>{{ taskStore.currentTask.taskName }} · {{ taskStore.currentTask.taskType }} · 截止 {{ taskStore.currentTask.deadline }}</p>
        </article>

        <article class="module-card">
          <div class="module-card__top">
            <strong>标准答案设置</strong>
            <span class="status-badge" :class="statusTone(currentAnswerStatus)">{{ statusText(currentAnswerStatus) }}</span>
          </div>
          <p>{{ currentAnswerText }}</p>
          <RouterLink :to="{ name: 'task-answers', params: { taskId: taskStore.currentTask.id } }" class="text-link">进入标准答案设置</RouterLink>
        </article>

        <article class="module-card">
          <div class="module-card__top">
            <strong>评分标准配置</strong>
            <span class="status-badge" :class="statusTone(currentRubricStatus)">{{ statusText(currentRubricStatus) }}</span>
          </div>
          <p>{{ currentRubricText }}</p>
          <div class="tag-row">
            <RouterLink :to="{ name: 'task-rubrics', params: { taskId: taskStore.currentTask.id } }" class="text-link">评分标准库</RouterLink>
            <RouterLink :to="{ name: 'task-rubric-generator', params: { taskId: taskStore.currentTask.id } }" class="text-link">文本生成 Rubric</RouterLink>
          </div>
        </article>

        <article class="module-card">
          <div class="module-card__top">
            <strong>Excel 结果表格式设置</strong>
            <span class="status-badge" :class="statusTone(currentTemplateStatus)">{{ statusText(currentTemplateStatus) }}</span>
          </div>
          <p>{{ currentTemplateText }}</p>
          <RouterLink :to="{ name: 'task-template', params: { taskId: taskStore.currentTask.id } }" class="text-link">进入 Excel 模板设置</RouterLink>
        </article>

        <article class="module-card">
          <div class="module-card__top">
            <strong>批量阅卷路径配置</strong>
            <span class="status-badge" :class="workspaceTone">{{ workspaceText }}</span>
          </div>
          <p>{{ currentWorkspaceText }}</p>
          <RouterLink :to="{ name: 'task-workspace', params: { taskId: taskStore.currentTask.id } }" class="text-link">进入路径配置</RouterLink>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const router = useRouter();
const taskStore = useTaskContextStore();
const configStore = useConfigStore();

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const currentAnswer = computed(() => configStore.answers.find((item) => item.current) ?? configStore.answers[0]);
const currentAnswerStatus = computed(() => currentAnswer.value?.status ?? "missing");
const currentRubricStatus = computed(() => configStore.currentRubric?.status ?? "missing");
const currentTemplateStatus = computed(() => configStore.currentTemplate?.status ?? "missing");

const currentAnswerText = computed(() =>
  currentAnswer.value
    ? `${currentAnswer.value.fileName} · ${currentAnswer.value.version} · ${currentAnswer.value.itemCount} 条`
    : "当前任务未激活标准答案版本。",
);
const currentRubricText = computed(() =>
  configStore.currentRubric
    ? `${configStore.currentRubric.name} · ${configStore.currentRubric.version}`
    : "当前任务未绑定评分标准。",
);
const currentTemplateText = computed(() =>
  configStore.currentTemplate
    ? `${configStore.currentTemplate.name} · ${configStore.currentTemplate.version}`
    : "当前任务未绑定 Excel 模板。",
);
const currentWorkspaceText = computed(() =>
  configStore.workspace
    ? `${configStore.workspace.rootPath} · ${configStore.workspace.lastMessage ?? "尚未检测路径"}`
    : "当前任务未加载路径配置。",
);
const workspaceTone = computed(() => (configStore.workspace?.status === "valid" ? "status-badge--good" : "status-badge--warn"));
const workspaceText = computed(() => {
  const map: Record<string, string> = { unchecked: "未检测", valid: "检测通过", invalid: "检测失败", initializing: "初始化中" };
  return map[configStore.workspace?.status ?? "unchecked"];
});

const statusTone = (status: string) => {
  if (status === "in_use" || status === "confirmed") return "status-badge--good";
  return "status-badge--warn";
};
const statusText = (status: string) => {
  const map: Record<string, string> = {
    missing: "未配置",
    draft: "草稿",
    confirmed: "已确认",
    in_use: "使用中",
    parse_failed: "解析失败",
  };
  return map[status] ?? status;
};

const goToGrading = async () => {
  if (!taskStore.currentTask) return;
  await router.push({ name: "task-grading", params: { taskId: taskStore.currentTask.id } });
};
</script>
