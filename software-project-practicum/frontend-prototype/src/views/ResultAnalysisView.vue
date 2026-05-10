<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.analytics">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">结果分析</div>
        <h2 class="hero-card__title">先判断本批成绩是否需要复核，再查看重点学生</h2>
        <p class="hero-card__text">
          分析页展示成绩分布、复核状态统计和学生结果列表，帮助教师优先定位需要确认或复核的样本。
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
      <article class="stat-card" :class="reviewRequiredCount > 0 ? 'stat-card--risk' : 'stat-card--good'">
        <div class="stat-card__label">待复核</div>
        <div class="stat-card__value">{{ reviewRequiredCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h3>结果列表</h3>
          <p class="panel__description">优先查看待复核、待确认或低置信度样本。置信度缺失时不按 0 处理。</p>
        </div>
        <div class="filter-toolbar">
          <input v-model="keyword" class="field__input field__input--search" type="text" placeholder="搜索学生姓名、学号或记录标识" />
          <button
            class="filter-chip"
            :class="{ 'filter-chip--active': attentionOnly }"
            type="button"
            @click="attentionOnly = !attentionOnly"
          >
            只看需关注样本
          </button>
        </div>
      </div>

      <div v-if="filteredStudents.length > 0" class="table-shell analysis-table-shell">
        <table class="table table--analysis">
          <thead>
            <tr>
              <th>学生</th>
              <th>总分</th>
              <th>复核状态</th>
              <th>风险摘要</th>
              <th>查看详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.id">
              <td>
                <div class="student-cell">
                  <strong>{{ student.name }}</strong>
                  <span>{{ student.studentNumber }}</span>
                  <span v-if="student.anonymousId && student.anonymousId !== '-'">记录 {{ student.anonymousId }}</span>
                </div>
              </td>
              <td>
                <div class="score-pill">{{ student.score }}</div>
              </td>
              <td>
                <span class="status-badge" :class="reviewStatusTone(student.reviewStatus)">
                  {{ reviewStatusLabel(student.reviewStatus) }}
                </span>
              </td>
              <td>
                <div class="risk-summary">
                  <span class="risk-summary__detail">
                    复核状态：{{ reviewStatusLabel(student.reviewStatus) }} · 置信度：{{ formatConfidence(student.confidence) }}
                  </span>
                  <div v-if="student.riskTags.length > 0" class="tag-row">
                    <span v-for="tag in student.riskTags" :key="tag" class="tag" :class="riskTagTone(student)">
                      {{ tag }}
                    </span>
                  </div>
                </div>
              </td>
              <td>
                <RouterLink :to="studentDetailRoute(student)" class="text-link">
                  查看详情
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
          <h3>复核状态统计</h3>
          <span class="panel__subtle">按最终成绩的复核状态汇总</span>
        </div>
        <div class="issue-stack">
          <article v-for="item in batchStore.analytics.topIssues" :key="item.title" class="issue-card issue-card--warn">
            <div class="issue-card__title">{{ item.title }}</div>
            <div class="issue-card__detail">{{ item.detail }}</div>
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
import {
  formatConfidence,
  hasLowConfidence,
  isAdjustedStatus,
  isPendingConfirmation,
  isReviewRequired,
  reviewStatusLabel,
  reviewStatusTone,
} from "../utils/review-status";

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

const reviewRequiredCount = computed(() => batchStore.analytics?.reviewRequiredCount ?? batchStore.analytics?.gateWarningCount ?? 0);

const hasAttention = (student: StudentRow) =>
  isReviewRequired(student.reviewStatus) ||
  isPendingConfirmation(student.reviewStatus) ||
  isAdjustedStatus(student.reviewStatus) ||
  hasLowConfidence(student.confidence) ||
  student.consistencyIssueCount > 1;

const riskTagTone = (student: StudentRow) => (reviewStatusTone(student.reviewStatus) === "status-badge--good" ? "tag--good" : "tag--warn");

const analysisVerdict = computed(() => {
  if (!batchStore.analytics) return "";
  if (reviewRequiredCount.value > 0) return "存在待复核样本";
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
  if (showClearFilters.value) return "可以清空搜索词或关闭“只看需关注样本”，恢复完整结果列表。";
  return "请先完成批量阅卷，或等待结果生成后再查看分析页面。";
});

const clearFilters = () => {
  keyword.value = "";
  attentionOnly.value = false;
};

const studentDetailRoute = (student: StudentRow) => ({
  name: "task-student-detail",
  params: { taskId: taskStore.currentTask?.id ?? "", studentId: student.id },
  query: {
    keyword: keyword.value,
    submissionId: student.submissionId ?? "",
    finalResultId: student.finalResultId ?? "",
  },
});
</script>
