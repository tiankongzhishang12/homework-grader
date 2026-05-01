<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.analytics">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">结果分析</div>
        <h2 class="hero-card__title">先判断这一批结果是否可信，再定位异常样本</h2>
        <p class="hero-card__text">
          分析页优先展示批次摘要、异常筛选和重点学生列表。老师先做风险判断，再进入单个样本详情查看证据与解释。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">平均分 {{ batchStore.analytics.averageScore }}</span>
        <span class="pill pill--warn">低置信度 {{ batchStore.analytics.lowConfidenceCount }}</span>
        <span class="pill">{{ analysisVerdict }}</span>
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
      <article class="stat-card" :class="batchStore.analytics.gateWarningCount > 0 ? 'stat-card--risk' : 'stat-card--good'">
        <div class="stat-card__label">门禁异常</div>
        <div class="stat-card__value">{{ batchStore.analytics.gateWarningCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h3>结果列表</h3>
          <p class="panel__description">优先查看异常样本。高级字段折叠到风险摘要中，避免表格信息过载。</p>
        </div>
        <div class="filter-toolbar">
          <input v-model="keyword" class="field__input field__input--search" type="text" placeholder="搜索学生姓名、学号或匿名 ID" />
          <button
            class="filter-chip"
            :class="{ 'filter-chip--active': attentionOnly }"
            type="button"
            @click="attentionOnly = !attentionOnly"
          >
            只看异常样本
          </button>
        </div>
      </div>

      <div v-if="filteredStudents.length > 0" class="student-result-card-list">
        <article v-for="student in filteredStudents" :key="student.id" class="student-result-card">
          <div class="student-result-card__top">
            <div>
              <strong>{{ student.name }}</strong>
              <span>{{ student.studentNumber }} · {{ student.anonymousId }}</span>
            </div>
            <div class="score-pill">{{ student.score }}</div>
          </div>
          <div class="student-result-card__meta">
            <span class="status-badge" :class="riskTone(student)">{{ riskLabel(student) }}</span>
            <span>{{ student.grade }}</span>
          </div>
          <p>置信度 {{ student.confidence }} · 门禁 {{ student.gateStatus }} · 缺失 {{ student.traceabilityGapCount }}</p>
          <div class="tag-row">
            <span v-for="tag in student.riskTags" :key="tag" class="tag" :class="riskTone(student) === 'status-badge--good' ? 'tag--good' : 'tag--warn'">
              {{ tag }}
            </span>
          </div>
          <RouterLink
            :to="{ name: 'task-student-detail', params: { taskId: taskStore.currentTask.id, studentId: student.id }, query: { keyword } }"
            class="action-button action-button--ghost"
          >
            查看解释
          </RouterLink>
        </article>
      </div>

      <div v-if="filteredStudents.length > 0" class="table-shell analysis-table-shell">
        <table class="table table--analysis">
          <thead>
            <tr>
              <th>学生</th>
              <th>总分</th>
              <th>等级</th>
              <th>风险摘要</th>
              <th>查看解释</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.id">
              <td>
                <div class="student-cell">
                  <strong>{{ student.name }}</strong>
                  <span>{{ student.studentNumber }}</span>
                  <span>{{ student.anonymousId }}</span>
                </div>
              </td>
              <td>
                <div class="score-pill">{{ student.score }}</div>
              </td>
              <td>{{ student.grade }}</td>
              <td>
                <div class="risk-summary">
                  <span class="status-badge" :class="riskTone(student)">{{ riskLabel(student) }}</span>
                  <span class="risk-summary__detail">
                    置信度 {{ student.confidence }} · 门禁 {{ student.gateStatus }} · 缺失 {{ student.traceabilityGapCount }}
                  </span>
                  <div class="tag-row">
                    <span v-for="tag in student.riskTags" :key="tag" class="tag" :class="riskTone(student) === 'status-badge--good' ? 'tag--good' : 'tag--warn'">
                      {{ tag }}
                    </span>
                  </div>
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

      <div v-else class="empty-state">
        <h4>{{ emptyStateTitle }}</h4>
        <p>{{ emptyStateDescription }}</p>
        <button v-if="showClearFilters" class="action-button action-button--ghost" type="button" @click="clearFilters">清空筛选</button>
      </div>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>分数分布</h3>
          <span class="panel__subtle">按分段查看整体表现</span>
        </div>
        <div class="chart-card">
          <div class="chart-bar-group">
            <div
              v-for="band in batchStore.analytics.scoreBands"
              :key="band.label"
              class="chart-bar chart-bar--m"
              :style="{ height: `${Math.max(28, band.value * 3)}px` }"
            >
              <span>{{ band.label }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>高频问题</h3>
          <span class="panel__subtle">优先关注重复出现的风险</span>
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
import type { StudentRow } from "../types";

const taskStore = useTaskContextStore();
const batchStore = useBatchStore();
const keyword = ref("");
const attentionOnly = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await batchStore.loadResults(taskId);
    }
  },
  { immediate: true },
);

const hasAttention = (student: StudentRow) =>
  student.confidence < 0.8 || student.traceabilityGapCount > 0 || student.consistencyIssueCount > 1 || student.gateStatus !== "通过";

const riskTone = (student: StudentRow) => {
  if (student.gateStatus !== "通过" || student.consistencyIssueCount > 1) return "status-badge--risk";
  if (student.confidence < 0.8 || student.traceabilityGapCount > 0 || student.consistencyIssueCount > 0) return "status-badge--warn";
  return "status-badge--good";
};

const riskLabel = (student: StudentRow) => {
  if (student.gateStatus !== "通过" || student.consistencyIssueCount > 1) return "必须复核";
  if (student.confidence < 0.8 || student.traceabilityGapCount > 0 || student.consistencyIssueCount > 0) return "建议抽查";
  return "可直接通过";
};

const analysisVerdict = computed(() => {
  if (!batchStore.analytics) return "";
  if (batchStore.analytics.gateWarningCount > 0) return "存在门禁异常";
  if (batchStore.analytics.lowConfidenceCount > 0) return "建议抽查低置信度样本";
  return "可进入导出确认";
});

const filteredStudents = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  return batchStore.students.filter((student) => {
    const matchesKeyword =
      !value || [student.name, student.studentNumber, student.anonymousId].some((item) => item.toLowerCase().includes(value));
    const matchesAttention = !attentionOnly.value || hasAttention(student);
    return matchesKeyword && matchesAttention;
  });
});

const showClearFilters = computed(() => keyword.value.trim().length > 0 || attentionOnly.value);

const emptyStateTitle = computed(() => {
  if (showClearFilters.value) return "没有符合当前筛选条件的学生";
  return "当前任务还没有可分析的结果数据";
});

const emptyStateDescription = computed(() => {
  if (showClearFilters.value) return "可以清空搜索词或关闭“只看异常样本”，恢复完整结果列表。";
  return "请先完成批量阅卷，或等待结果生成后再查看分析页面。";
});

const clearFilters = () => {
  keyword.value = "";
  attentionOnly.value = false;
};
</script>
