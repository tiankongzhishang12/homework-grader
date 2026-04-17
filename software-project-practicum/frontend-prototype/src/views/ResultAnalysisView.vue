<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.analytics">
    <div class="hero-card">
      <div>
        <div class="eyebrow">结果分析</div>
        <h2 class="hero-card__title">先判断这一批结果是否可信，再抽查典型样本解释</h2>
        <p class="hero-card__text">
          当前页面用于批次摘要、结果筛选、统计分布和高频问题展示。异常信息只作为质量提示，不生成人工复核待办。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">平均分：{{ batchStore.analytics.averageScore }}</span>
        <span class="pill">低置信度：{{ batchStore.analytics.lowConfidenceCount }}</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">总人数</div>
        <div class="stat-card__value">{{ batchStore.analytics.totalStudents }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">平均分</div>
        <div class="stat-card__value">{{ batchStore.analytics.averageScore }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">低置信度</div>
        <div class="stat-card__value">{{ batchStore.analytics.lowConfidenceCount }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">门禁异常</div>
        <div class="stat-card__value">{{ batchStore.analytics.gateWarningCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h3>结果列表</h3>
          <p class="panel__description">支持按关键词筛选，并进入样本解释页后保留当前查询条件。</p>
        </div>
        <div class="filter-toolbar">
          <input v-model="keyword" class="field__input field__input--search" type="text" placeholder="搜索学生 / 学号 / 匿名 ID" />
        </div>
      </div>

      <div class="table-shell">
        <table class="table">
          <thead>
            <tr>
              <th>学号</th>
              <th>姓名</th>
              <th>匿名 ID</th>
              <th>总分</th>
              <th>等级</th>
              <th>置信度</th>
              <th>门禁状态</th>
              <th>追踪缺失数</th>
              <th>一致性问题数</th>
              <th>风险标签</th>
              <th>查看解释</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.id">
              <td>{{ student.studentNumber }}</td>
              <td>{{ student.name }}</td>
              <td>{{ student.anonymousId }}</td>
              <td><strong>{{ student.score }}</strong></td>
              <td>{{ student.grade }}</td>
              <td>{{ student.confidence }}</td>
              <td>{{ student.gateStatus }}</td>
              <td>{{ student.traceabilityGapCount }}</td>
              <td>{{ student.consistencyIssueCount }}</td>
              <td>
                <div class="tag-row">
                  <span v-for="tag in student.riskTags" :key="tag" class="tag" :class="tag.includes('低') || tag.includes('缺失') ? 'tag--warn' : 'tag--good'">{{ tag }}</span>
                </div>
              </td>
              <td>
                <RouterLink
                  :to="{ name: 'task-student-detail', params: { taskId: taskStore.currentTask.id, studentId: student.id }, query: { keyword } }"
                  class="text-link"
                >
                  查看解释
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>分数分布</h3>
        </div>
        <div class="chart-card">
          <div class="chart-bar-group">
            <div v-for="band in batchStore.analytics.scoreBands" :key="band.label" class="chart-bar chart-bar--m" :style="{ height: `${Math.max(18, band.value * 3)}px` }">
              <span>{{ band.label }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>高频问题</h3>
        </div>
        <div class="issue-stack">
          <article v-for="item in batchStore.analytics.topIssues" :key="item.title" class="issue-card issue-card--warn">
            <div class="issue-card__title">{{ item.title }}</div>
            <div class="issue-card__detail">{{ item.count }} 次 · {{ item.detail }}</div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useBatchStore } from "../stores/batch";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const batchStore = useBatchStore();
const keyword = ref("");

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await batchStore.loadResults(taskId);
    }
  },
  { immediate: true },
);

const filteredStudents = computed(() => {
  const value = keyword.value.trim();
  if (!value) return batchStore.students;
  return batchStore.students.filter((student) =>
    [student.name, student.studentNumber, student.anonymousId].some((item) => item.toLowerCase().includes(value.toLowerCase())),
  );
});
</script>
