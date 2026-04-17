<template>
  <section class="view">
    <div class="hero-card">
      <div>
        <div class="eyebrow">任务列表</div>
        <h2 class="hero-card__title">先选定班级和课程任务，再进入该任务的完整工作台</h2>
        <p class="hero-card__text">
          首发版采用“先选任务，再进入任务工作台”的结构。老师只需从当前负责的任务中选择一项，再继续完成配置、自动阅卷、结果分析和导出。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">教师单端</span>
        <span class="pill">桌面优先</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">当前任务数</div>
        <div class="stat-card__value">{{ taskStore.tasks.length }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">待补配置任务</div>
        <div class="stat-card__value">{{ notReadyCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">已完成批次</div>
        <div class="stat-card__value">{{ completedCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">评分中批次</div>
        <div class="stat-card__value">{{ runningCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>教师可见任务</h3>
          <p class="panel__description">任务卡片按“配置是否就绪”和“当前批次状态”展示下一步动作。</p>
        </div>
        <button class="action-button action-button--ghost" :disabled="taskStore.loading" @click="taskStore.loadTasks()">
          {{ taskStore.loading ? "刷新中..." : "刷新任务列表" }}
        </button>
      </div>

      <div class="task-list-grid">
        <article v-for="task in taskStore.tasks" :key="task.id" class="task-list-card">
          <div class="task-list-card__top">
            <div>
              <div class="rubric-card__title">{{ task.taskName }}</div>
              <div class="rubric-card__meta">{{ task.courseName }} · {{ task.className }}</div>
            </div>
            <span class="status-badge" :class="task.configReady ? 'status-badge--good' : 'status-badge--warn'">
              {{ task.configReady ? "配置已就绪" : "待补配置" }}
            </span>
          </div>
          <p class="rubric-card__summary">{{ task.description }}</p>
          <div class="summary-grid">
            <div class="summary-item"><span>任务类型</span><strong>{{ task.taskType }}</strong></div>
            <div class="summary-item"><span>提交进度</span><strong>{{ task.submittedCount }}/{{ task.studentCount }}</strong></div>
            <div class="summary-item"><span>配置完成度</span><strong>{{ task.configProgress }}%</strong></div>
            <div class="summary-item"><span>批次状态</span><strong>{{ batchStatusMap[task.batchStatus] }}</strong></div>
          </div>
          <div class="task-list-card__footer">
            <div class="panel__description">{{ task.nextAction }}</div>
            <RouterLink :to="{ name: 'task-config', params: { taskId: task.id } }" class="action-button">进入任务工作台</RouterLink>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();

onMounted(async () => {
  if (taskStore.tasks.length === 0) {
    await taskStore.loadTasks();
  }
});

const notReadyCount = computed(() => taskStore.tasks.filter((item) => !item.configReady).length);
const completedCount = computed(() => taskStore.tasks.filter((item) => item.batchStatus === "completed").length);
const runningCount = computed(() => taskStore.tasks.filter((item) => ["preprocessing", "scoring", "aggregating"].includes(item.batchStatus)).length);

const batchStatusMap = {
  idle: "待开始",
  preprocessing: "预处理中",
  scoring: "评分中",
  aggregating: "汇总中",
  completed: "已完成",
  failed: "失败",
} as const;
</script>
