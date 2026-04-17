<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">批量阅卷</div>
        <h2 class="hero-card__title">只看执行状态和质量提示，不进入人工复核流程</h2>
        <p class="hero-card__text">
          当前阶段的阅卷页是自动阅卷执行台。老师在这里关注批次状态、进度轮询、日志摘要和质量提示；评分完成后再进入结果分析与导出。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill" :class="taskStore.canStartBatch ? 'pill--good' : 'pill--warn'">
          {{ taskStore.canStartBatch ? "配置已满足执行条件" : "当前仍有阻断项" }}
        </span>
        <span class="pill">{{ progressLabel }}</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">批次状态</div>
        <div class="stat-card__value stat-card__value--small">{{ progressLabel }}</div>
      </article>
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">已完成评分</div>
        <div class="stat-card__value">{{ batchStore.progress?.completed ?? 0 }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">总提交数</div>
        <div class="stat-card__value">{{ batchStore.progress?.total ?? taskStore.currentTask.submittedCount }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">质量提示</div>
        <div class="stat-card__value">{{ qualityCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>执行操作</h3>
          <p class="panel__description">进度轮询默认 3 秒一次，页面隐藏时自动暂停，返回后继续。</p>
        </div>
        <div class="toolbar__actions">
          <button class="action-button" :disabled="!taskStore.canStartBatch || batchStore.loading || isRunning" @click="startBatch">
            {{ batchStore.loading ? "启动中..." : "开始阅卷" }}
          </button>
          <button class="action-button action-button--ghost" :disabled="batchStore.loading" @click="refreshProgress">刷新进度</button>
          <button class="action-button action-button--ghost" :disabled="batchStore.loading" @click="loadLogs">查看日志摘要</button>
          <RouterLink :to="{ name: 'task-analysis', params: { taskId: taskStore.currentTask.id } }" class="action-button action-button--ghost">
            进入结果分析
          </RouterLink>
        </div>
      </div>

      <article class="detail-block detail-block--highlight">
        <h4>当前步骤</h4>
        <p>{{ batchStore.progress?.currentStepLabel ?? "等待开始阅卷" }}</p>
      </article>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>质量提示</h3>
        </div>
        <div class="issue-stack">
          <article v-for="item in batchStore.progress?.qualityFlags ?? []" :key="item.flag" class="issue-card issue-card--warn">
            <div class="issue-card__title">{{ item.label }}</div>
            <div class="issue-card__detail">{{ item.count }} 份样本</div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>日志摘要</h3>
        </div>
        <ul class="detail-list">
          <li v-for="item in batchStore.logs" :key="`${item.time}-${item.message}`">[{{ item.level }}] {{ item.time }} · {{ item.message }}</li>
        </ul>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from "vue";
import { RouterLink } from "vue-router";
import { useBatchStore } from "../stores/batch";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const batchStore = useBatchStore();

const progressLabel = computed(() => {
  const map: Record<string, string> = {
    idle: "待开始",
    preprocessing: "预处理中",
    scoring: "评分中",
    aggregating: "汇总中",
    completed: "已完成",
    failed: "失败",
  };
  return map[batchStore.progress?.status ?? taskStore.currentTask?.batchStatus ?? "idle"];
});

const qualityCount = computed(() => (batchStore.progress?.qualityFlags ?? []).reduce((sum, item) => sum + item.count, 0));
const isRunning = computed(() => ["preprocessing", "scoring", "aggregating"].includes(batchStore.progress?.status ?? ""));

const syncVisibility = async () => {
  if (!taskStore.currentTask) return;
  if (document.visibilityState === "visible" && isRunning.value) {
    await batchStore.loadProgress(taskStore.currentTask.id, true);
  } else if (document.visibilityState === "hidden") {
    batchStore.stopPolling();
  }
};

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await batchStore.loadProgress(taskId, true);
      await batchStore.loadLogs(taskId);
    }
  },
  { immediate: true },
);

document.addEventListener("visibilitychange", syncVisibility);

onUnmounted(() => {
  document.removeEventListener("visibilitychange", syncVisibility);
  batchStore.stopPolling();
});

const startBatch = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.startBatch(taskStore.currentTask.id);
};

const refreshProgress = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.loadProgress(taskStore.currentTask.id, true);
};

const loadLogs = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.loadLogs(taskStore.currentTask.id);
};
</script>
