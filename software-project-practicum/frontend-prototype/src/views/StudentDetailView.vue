<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.currentStudent">
    <article class="detail-hero detail-hero--summary">
      <div class="detail-hero__content">
        <div class="eyebrow">学生详情</div>
        <h2 class="detail-hero__name">{{ batchStore.currentStudent.name }} / {{ batchStore.currentStudent.studentNumber }}</h2>
        <p class="detail-hero__summary">{{ batchStore.currentStudent.summary }}</p>
        <div class="tag-row">
          <span v-if="batchStore.currentStudent.anonymousId && batchStore.currentStudent.anonymousId !== '-'" class="tag">
            提交记录 #{{ batchStore.currentStudent.anonymousId }}
          </span>
          <span class="tag" :class="hasLowConfidence(batchStore.currentStudent.confidence) ? 'tag--warn' : 'tag--good'">
            置信度：{{ formatConfidence(batchStore.currentStudent.confidence) }}
          </span>
          <span class="tag">复核状态：{{ reviewStatusLabel(batchStore.currentStudent.reviewStatus) }}</span>
          <span v-if="batchStore.currentStudent.grade && batchStore.currentStudent.grade !== '-'" class="tag">{{ batchStore.currentStudent.grade }}</span>
        </div>
      </div>

      <div class="detail-hero__aside">
        <div class="detail-score">
          <div class="detail-score__main">{{ batchStore.currentStudent.score }}</div>
          <div class="detail-score__sub">当前总分</div>
        </div>
        <RouterLink
          :to="{ name: 'task-analysis', params: { taskId: taskStore.currentTask.id }, query: { keyword: route.query.keyword ?? '' } }"
          class="action-button action-button--ghost"
        >
          返回结果列表
        </RouterLink>
        <button
          class="action-button"
          type="button"
          :disabled="batchStore.loading || !batchStore.currentStudent.finalResultId || isConfirmedStatus(batchStore.currentStudent.reviewStatus)"
          @click="confirmCurrentStudent"
        >
          {{ isConfirmedStatus(batchStore.currentStudent.reviewStatus) ? "已确认" : "教师确认" }}
        </button>
      </div>
    </article>

    <section class="panel review-summary-panel">
      <div class="review-summary-panel__headline">
        <div>
          <span class="eyebrow">复核摘要</span>
          <h3>{{ reviewRecommendation }}</h3>
        </div>
        <span class="status-badge" :class="reviewTone">{{ reviewStatusLabel(batchStore.currentStudent.reviewStatus) }}</span>
      </div>
      <div class="review-summary-grid">
        <article class="summary-item">
          <span>总分</span>
          <strong>{{ batchStore.currentStudent.score }}</strong>
        </article>
        <article class="summary-item">
          <span>置信度</span>
          <strong>{{ formatConfidence(batchStore.currentStudent.confidence) }}</strong>
        </article>
        <article class="summary-item">
          <span>复核状态</span>
          <strong>{{ reviewStatusLabel(batchStore.currentStudent.reviewStatus) }}</strong>
        </article>
        <article class="summary-item">
          <span>评分项</span>
          <strong>{{ batchStore.currentStudent.dimensions.length }}</strong>
        </article>
      </div>
      <ul class="detail-list review-summary-panel__findings">
        <li v-for="item in batchStore.currentStudent.qualityFindings.slice(0, 3)" :key="item">{{ item }}</li>
      </ul>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>首要结论</h3>
          <span class="panel__subtle">先看成绩和复核结论，再查看评分项明细</span>
        </div>
        <ul class="detail-list">
          <li v-for="item in batchStore.currentStudent.qualityFindings" :key="item">{{ item }}</li>
        </ul>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>改进建议</h3>
          <span class="panel__subtle">来自评分项明细中的可反馈内容</span>
        </div>
        <div class="issue-stack">
          <article v-for="item in improvementHighlights" :key="item.id" class="detail-block detail-block--highlight">
            <h4>{{ item.name }}</h4>
            <p>{{ item.improvement }}</p>
          </article>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>评分项明细</h3>
          <p class="panel__description">展示每个评分项的得分、证据、评语和建议，供教师确认或复核。</p>
        </div>
      </div>

      <div class="issue-stack">
        <article v-for="item in batchStore.currentStudent.dimensions" :key="item.id" class="dimension-summary-card">
          <div class="dimension-summary-card__top">
            <div>
              <h4>{{ item.name }}</h4>
              <p class="dimension-summary-card__meta">得分 {{ item.score }}/{{ item.maxScore }} · 置信度：{{ formatConfidence(item.confidence) }}</p>
            </div>
            <span class="pill">{{ scoreToneLabel(item.score, item.maxScore) }}</span>
          </div>

          <div class="content-grid content-grid--two">
            <article class="detail-list-card">
              <h4>评分证据</h4>
              <p>{{ item.evidence }}</p>
            </article>
            <article class="detail-list-card detail-list-card--risk">
              <h4>需关注内容</h4>
              <ul v-if="item.missing.length > 0">
                <li v-for="miss in item.missing" :key="miss">{{ miss }}</li>
              </ul>
              <p v-else>当前评分项暂未返回需关注内容。</p>
            </article>
          </div>

          <article class="detail-block">
            <h4>评语</h4>
            <p>{{ item.reasoning }}</p>
          </article>

          <article class="detail-block detail-block--highlight">
            <h4>改进建议</h4>
            <p>{{ item.improvement }}</p>
          </article>
        </article>
      </div>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>追踪分析</h3>
          <span class="panel__subtle">结构化证据追踪信息</span>
        </div>

        <div v-if="hasTraceabilityData" class="traceability-grid traceability-grid--compact">
          <article class="trace-column">
            <h4>需求清单</h4>
            <ul>
              <li v-for="item in batchStore.currentStudent.traceability.requirements" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="trace-column">
            <h4>概要设计覆盖</h4>
            <div v-for="item in batchStore.currentStudent.traceability.hldCoverage" :key="item.requirement" class="trace-card">
              <div class="trace-card__top">
                <span>{{ item.requirement }}</span>
                <span class="trace-status" :class="`trace-status--${item.status}`">{{ coverageLabel(item.status) }}</span>
              </div>
              <p>{{ item.evidence }}</p>
            </div>
          </article>
        </div>

        <div v-if="hasTraceabilityData && batchStore.currentStudent.traceability.uncoveredRequirements.length > 0" class="alert-strip">
          <strong>未覆盖需求：</strong>
          <span>{{ batchStore.currentStudent.traceability.uncoveredRequirements.join("；") }}</span>
        </div>
        <div v-if="!hasTraceabilityData" class="empty-state">当前评分结果暂未返回结构化追踪信息。</div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>复核处理建议</h3>
          <span class="panel__subtle">辅助判断该学生成绩是否需要人工处理</span>
        </div>

        <div class="gate-grid">
          <article v-for="item in batchStore.currentStudent.gates" :key="item.name" class="gate-card">
            <div class="gate-card__top">
              <strong>{{ item.name }}</strong>
              <span class="status-badge" :class="item.passed ? 'status-badge--good' : 'status-badge--risk'">
                {{ item.passed ? "已处理" : "需处理" }}
              </span>
            </div>
            <div class="gate-card__meta">{{ item.detail }}</div>
            <div class="gate-card__meta">{{ item.onFail }}</div>
          </article>
        </div>

        <article v-if="hasMaterialSummary" class="detail-list-card">
          <h4>原始材料摘要</h4>
          <ul>
            <li>文档数：{{ batchStore.currentStudent.materials.documentCount }}</li>
            <li>字数：{{ batchStore.currentStudent.materials.wordCount }}</li>
            <li>图片数：{{ batchStore.currentStudent.materials.imageCount }}</li>
            <li v-if="batchStore.currentStudent.materials.roles.length > 0">角色：{{ batchStore.currentStudent.materials.roles.join("；") }}</li>
            <li v-for="log in batchStore.currentStudent.materials.logs" :key="log">{{ log }}</li>
          </ul>
        </article>
        <div v-else class="empty-state">当前评分结果暂未返回原始材料摘要。</div>
      </section>
    </div>
  </section>

  <section v-else class="view">
    <section class="panel">
      <div class="empty-state">
        <h4>{{ batchStore.loading ? "正在加载学生详情" : "未找到该学生的评分详情" }}</h4>
        <p>
          {{
            batchStore.loading
              ? "系统正在读取学生评分详情，请稍候。"
              : "当前学生 ID 没有匹配到评分详情，请返回结果分析页重新选择。"
          }}
        </p>
        <div class="toolbar__actions">
          <RouterLink :to="{ name: 'task-analysis', params: { taskId: route.params.taskId } }" class="action-button action-button--ghost">
            返回结果分析
          </RouterLink>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useBatchStore } from "../stores/batch";
import { useTaskContextStore } from "../stores/task-context";
import {
  formatConfidence,
  hasLowConfidence,
  isAdjustedStatus,
  isConfirmedStatus,
  isPendingConfirmation,
  isTeacherActionRequired,
  reviewStatusLabel,
  reviewStatusTone,
} from "../utils/review-status";

const route = useRoute();
const taskStore = useTaskContextStore();
const batchStore = useBatchStore();

watch(
  () => [taskStore.currentTask?.id, route.params.studentId, route.query.submissionId, route.query.finalResultId] as const,
  async ([taskId, studentId, submissionId, finalResultId]) => {
    if (taskId && studentId) {
      await batchStore.loadStudent(
        String(studentId),
        taskId,
        typeof submissionId === "string" ? submissionId : undefined,
        typeof finalResultId === "string" ? finalResultId : undefined,
      );
    }
  },
  { immediate: true },
);

const confirmCurrentStudent = async () => {
  await batchStore.confirmCurrentStudent();
};

const improvementHighlights = computed(() => batchStore.currentStudent?.dimensions.slice(0, 3) ?? []);
const hasTraceabilityData = computed(() => {
  const traceability = batchStore.currentStudent?.traceability;
  if (!traceability) return false;
  return (
    traceability.requirements.length > 0 ||
    traceability.hldCoverage.length > 0 ||
    traceability.lldCoverage.length > 0 ||
    traceability.uncoveredRequirements.length > 0
  );
});
const hasMaterialSummary = computed(() => {
  const materials = batchStore.currentStudent?.materials;
  if (!materials) return false;
  return materials.documentCount > 0 || materials.wordCount > 0 || materials.imageCount > 0 || materials.roles.length > 0 || materials.logs.length > 0;
});
const reviewRecommendation = computed(() => {
  const student = batchStore.currentStudent;
  if (!student) return "";
  if (isTeacherActionRequired(student.reviewStatus)) {
    return isPendingConfirmation(student.reviewStatus) ? "当前成绩需要教师确认" : "当前成绩需要教师复核";
  }
  if (hasLowConfidence(student.confidence)) return "建议抽查低置信度评分";
  if (isConfirmedStatus(student.reviewStatus)) return "当前成绩已确认";
  if (isAdjustedStatus(student.reviewStatus)) return "当前成绩已调整";
  return "当前成绩可进入确认流程";
});
const reviewTone = computed(() => reviewStatusTone(batchStore.currentStudent?.reviewStatus));

const scoreToneLabel = (score: number, maxScore: number) => {
  const ratio = maxScore === 0 ? 0 : score / maxScore;
  if (ratio >= 0.85) return "表现稳定";
  if (ratio >= 0.6) return "建议关注";
  return "重点改进";
};

const coverageLabel = (status: "covered" | "weak" | "missing") => {
  const map = {
    covered: "已覆盖",
    weak: "覆盖较弱",
    missing: "未覆盖",
  } as const;
  return map[status];
};
</script>
