<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.analytics">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">结果分析</div>
        <h2 class="hero-card__title">先处理高优先级样本，再完成成绩确认</h2>
        <p class="hero-card__text">
          结果分析页按复核状态、风险类型和分数区间筛选学生，并默认把最需要教师处理的样本排在前面。
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
        <div class="stat-card__label">待处理</div>
        <div class="stat-card__value">{{ reviewRequiredCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h3>结果列表</h3>
          <p class="panel__description">按状态、风险和分数快速缩小范围，优先处理高优先级学生。</p>
        </div>

        <div class="analysis-filter-grid">
          <label class="field">
            <span>搜索</span>
            <input v-model="keyword" class="field__input" type="text" placeholder="学生姓名、学号或提交记录" />
          </label>
          <label class="field">
            <span>复核状态</span>
            <select v-model="statusFilter" class="field__input">
              <option v-for="option in statusFilterOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>风险类型</span>
            <select v-model="riskFilter" class="field__input">
              <option v-for="option in riskFilterOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>分数区间</span>
            <select v-model="scoreBandFilter" class="field__input">
              <option v-for="option in scoreBandFilterOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>排序</span>
            <select v-model="sortMode" class="field__input">
              <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <div class="analysis-filter-actions">
            <button
              class="filter-chip"
              :class="{ 'filter-chip--active': attentionOnly }"
              type="button"
              @click="toggleAttentionOnly"
            >
              只看需关注样本
            </button>
            <button v-if="showClearFilters" class="action-button action-button--ghost" type="button" @click="clearFilters">清空筛选</button>
          </div>
        </div>

        <div class="analysis-result-count" :class="{ 'analysis-result-count--filtered': showClearFilters }">
          {{ showClearFilters ? "已应用筛选条件，" : "" }}当前显示 {{ filteredStudents.length }} / {{ batchStore.students.length }} 名学生
        </div>
      </div>

      <div v-if="filteredStudents.length > 0" class="table-shell analysis-table-shell">
        <table class="table table--analysis">
          <thead>
            <tr>
              <th>学生</th>
              <th>总分</th>
              <th>复核状态</th>
              <th>置信度</th>
              <th>处理优先级</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.id">
              <td>
                <div class="student-cell">
                  <strong>{{ student.name }}</strong>
                  <span>{{ student.studentNumber }}</span>
                  <span v-if="student.anonymousId && student.anonymousId !== '-'">提交记录 #{{ student.anonymousId }}</span>
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
              <td>{{ formatConfidence(student.confidence) }}</td>
              <td>
                <span class="tag" :class="studentPriorityTone(student)">
                  {{ studentPriorityLabel(student) }}
                </span>
              </td>
              <td>
                <RouterLink :to="studentDetailRoute(student)" class="text-link">查看详情</RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="filteredStudents.length > 0" class="student-result-card-list">
        <article v-for="student in filteredStudents" :key="student.id" class="student-result-card">
          <div class="student-result-card__top">
            <div>
              <strong>{{ student.name }}</strong>
              <span>{{ student.studentNumber }}</span>
              <span v-if="student.anonymousId && student.anonymousId !== '-'">提交记录 #{{ student.anonymousId }}</span>
            </div>
            <div class="score-pill">{{ student.score }}</div>
          </div>
          <div class="student-result-card__meta">
            <span class="status-badge" :class="reviewStatusTone(student.reviewStatus)">
              {{ reviewStatusLabel(student.reviewStatus) }}
            </span>
            <span class="tag" :class="studentPriorityTone(student)">
              {{ studentPriorityLabel(student) }}
            </span>
          </div>
          <p>置信度：{{ formatConfidence(student.confidence) }}</p>
          <RouterLink :to="studentDetailRoute(student)" class="action-button action-button--ghost">查看详情</RouterLink>
        </article>
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
          <span class="panel__subtle">按分段查看人数和占比</span>
        </div>
        <div class="score-band-list">
          <article v-for="band in scoreDistribution" :key="band.label" class="score-band-row">
            <div>
              <strong>{{ band.label }}</strong>
              <span>{{ band.value }} 人，占 {{ band.percent }}%</span>
            </div>
            <div class="score-band-meter">
              <span :style="{ width: `${band.percent}%` }"></span>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>复核状态分布</h3>
          <span class="panel__subtle">按最终成绩的复核状态汇总</span>
        </div>
        <div class="issue-stack">
          <article v-for="item in batchStore.analytics.topIssues" :key="item.title" class="issue-card issue-card--warn">
            <div class="issue-card__title">
              <span>{{ item.title }}</span>
              <strong>{{ item.count }} 人</strong>
            </div>
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
  canonicalReviewStatus,
  formatConfidence,
  hasLowConfidence,
  isAdjustedStatus,
  isConfirmedStatus,
  isPendingConfirmation,
  isReviewRequired,
  isTeacherActionRequired,
  reviewStatusLabel,
  reviewStatusTone,
} from "../utils/review-status";

type StatusFilter = "all" | "AI_GENERATED" | "REVIEW_REQUIRED" | "CONFIRMED" | "ADJUSTED" | "PUBLISHED";
type RiskFilter = "all" | "teacher_action_required" | "low_confidence" | "adjusted";
type ScoreBandFilter = "all" | "lt60" | "60-69" | "70-79" | "80-89" | "90plus";
type SortMode = "priority" | "score_asc" | "score_desc" | "confidence_asc" | "student_no_asc";
type StudentPriority = "high" | "medium" | "done";

const taskStore = useTaskContextStore();
const batchStore = useBatchStore();
const keyword = ref("");
const attentionOnly = ref(false);
const statusFilter = ref<StatusFilter>("all");
const riskFilter = ref<RiskFilter>("all");
const scoreBandFilter = ref<ScoreBandFilter>("all");
const sortMode = ref<SortMode>("priority");

const statusFilterOptions: Array<{ label: string; value: StatusFilter }> = [
  { label: "全部", value: "all" },
  { label: "待教师确认", value: "AI_GENERATED" },
  { label: "待教师复核", value: "REVIEW_REQUIRED" },
  { label: "已确认", value: "CONFIRMED" },
  { label: "已调整", value: "ADJUSTED" },
  { label: "已发布", value: "PUBLISHED" },
];

const riskFilterOptions: Array<{ label: string; value: RiskFilter }> = [
  { label: "全部", value: "all" },
  { label: "需教师处理", value: "teacher_action_required" },
  { label: "低置信度", value: "low_confidence" },
  { label: "已调整", value: "adjusted" },
];

const scoreBandFilterOptions: Array<{ label: string; value: ScoreBandFilter }> = [
  { label: "全部", value: "all" },
  { label: "低于 60", value: "lt60" },
  { label: "60-69", value: "60-69" },
  { label: "70-79", value: "70-79" },
  { label: "80-89", value: "80-89" },
  { label: "90 以上", value: "90plus" },
];

const sortOptions: Array<{ label: string; value: SortMode }> = [
  { label: "待处理优先", value: "priority" },
  { label: "分数从低到高", value: "score_asc" },
  { label: "分数从高到低", value: "score_desc" },
  { label: "置信度从低到高", value: "confidence_asc" },
  { label: "学号升序", value: "student_no_asc" },
];

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await batchStore.loadResults(taskId);
    }
  },
  { immediate: true },
);

watch(riskFilter, (value) => {
  attentionOnly.value = value === "teacher_action_required";
});

const reviewRequiredCount = computed(() => batchStore.analytics?.reviewRequiredCount ?? batchStore.analytics?.gateWarningCount ?? 0);

const studentPriority = (student: StudentRow): StudentPriority => {
  if (isReviewRequired(student.reviewStatus) || hasLowConfidence(student.confidence)) return "high";
  if (isPendingConfirmation(student.reviewStatus) || isAdjustedStatus(student.reviewStatus)) return "medium";
  if (isConfirmedStatus(student.reviewStatus)) return "done";
  return "medium";
};

const priorityRank = (student: StudentRow) => {
  const rank: Record<StudentPriority, number> = { high: 0, medium: 1, done: 2 };
  return rank[studentPriority(student)];
};

const studentPriorityLabel = (student: StudentRow) => {
  const priority = studentPriority(student);
  if (priority === "high") return "高优先级";
  if (priority === "medium") return "中优先级";
  return "已处理";
};

const studentPriorityTone = (student: StudentRow) => {
  const priority = studentPriority(student);
  if (priority === "high") return "status-badge--risk";
  if (priority === "medium") return "tag--warn";
  return "tag--good";
};

const analysisVerdict = computed(() => {
  if (!batchStore.analytics) return "";
  if (reviewRequiredCount.value > 0) return "存在待处理样本";
  if (batchStore.analytics.lowConfidenceCount > 0) return "建议抽查低置信度样本";
  return "可进入导出确认";
});

const matchesKeyword = (student: StudentRow, value: string) =>
  !value || [student.name, student.studentNumber, student.anonymousId].some((item) => item.toLowerCase().includes(value));

const matchesStatusFilter = (student: StudentRow) =>
  statusFilter.value === "all" || canonicalReviewStatus(student.reviewStatus) === statusFilter.value;

const matchesRiskFilter = (student: StudentRow) => {
  switch (riskFilter.value) {
    case "teacher_action_required":
      return isTeacherActionRequired(student.reviewStatus);
    case "low_confidence":
      return hasLowConfidence(student.confidence);
    case "adjusted":
      return isAdjustedStatus(student.reviewStatus);
    default:
      return true;
  }
};

const matchesScoreBandFilter = (student: StudentRow) => {
  switch (scoreBandFilter.value) {
    case "lt60":
      return student.score < 60;
    case "60-69":
      return student.score >= 60 && student.score < 70;
    case "70-79":
      return student.score >= 70 && student.score < 80;
    case "80-89":
      return student.score >= 80 && student.score < 90;
    case "90plus":
      return student.score >= 90;
    default:
      return true;
  }
};

const studentNoSortValue = (student: StudentRow) => (student.studentNumber === "学号缺失" ? "" : student.studentNumber);

const confidenceSortValue = (student: StudentRow) =>
  student.confidence === null || student.confidence === undefined || student.confidence <= 0 ? Number.POSITIVE_INFINITY : student.confidence;

const sortStudents = (students: StudentRow[]) =>
  [...students].sort((a, b) => {
    if (sortMode.value === "score_asc") return a.score - b.score;
    if (sortMode.value === "score_desc") return b.score - a.score;
    if (sortMode.value === "confidence_asc") return confidenceSortValue(a) - confidenceSortValue(b);
    if (sortMode.value === "student_no_asc") return studentNoSortValue(a).localeCompare(studentNoSortValue(b), "zh-CN", { numeric: true });
    return priorityRank(a) - priorityRank(b) || a.score - b.score || studentNoSortValue(a).localeCompare(studentNoSortValue(b), "zh-CN", { numeric: true });
  });

const filteredStudents = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  const result = batchStore.students
    .filter((student) => matchesKeyword(student, value))
    .filter(matchesStatusFilter)
    .filter(matchesRiskFilter)
    .filter(matchesScoreBandFilter);
  return sortStudents(result);
});

const scoreDistribution = computed(() => {
  const total = batchStore.analytics?.totalStudents ?? 0;
  return (batchStore.analytics?.scoreBands ?? []).map((band) => ({
    ...band,
    percent: total > 0 ? Number(((band.value / total) * 100).toFixed(1)) : 0,
  }));
});

const showClearFilters = computed(
  () =>
    keyword.value.trim().length > 0 ||
    attentionOnly.value ||
    statusFilter.value !== "all" ||
    riskFilter.value !== "all" ||
    scoreBandFilter.value !== "all" ||
    sortMode.value !== "priority",
);

const emptyStateTitle = computed(() => {
  if (showClearFilters.value) return "没有符合当前筛选条件的学生";
  return "当前任务还没有可分析的结果数据";
});

const emptyStateDescription = computed(() => {
  if (showClearFilters.value) return "可以清空搜索词、状态、风险或分数筛选，恢复完整结果列表。";
  return "请先完成批量阅卷，或等待结果生成后再查看分析页面。";
});

const toggleAttentionOnly = () => {
  attentionOnly.value = !attentionOnly.value;
  riskFilter.value = attentionOnly.value ? "teacher_action_required" : "all";
};

const clearFilters = () => {
  keyword.value = "";
  attentionOnly.value = false;
  statusFilter.value = "all";
  riskFilter.value = "all";
  scoreBandFilter.value = "all";
  sortMode.value = "priority";
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
