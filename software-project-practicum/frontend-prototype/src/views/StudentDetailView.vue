<template>
  <section class="view" v-if="taskStore.currentTask && batchStore.currentStudent">
    <article class="detail-hero detail-hero--summary">
      <div class="detail-hero__content">
        <div class="eyebrow">样本解释</div>
        <h2 class="detail-hero__name">{{ batchStore.currentStudent.name }} / {{ batchStore.currentStudent.studentNumber }}</h2>
        <p class="detail-hero__summary">{{ batchStore.currentStudent.summary }}</p>
        <div class="tag-row">
          <span class="tag">{{ batchStore.currentStudent.anonymousId }}</span>
          <span class="tag" :class="batchStore.currentStudent.confidence < 0.8 ? 'tag--warn' : 'tag--good'">
            置信度 {{ batchStore.currentStudent.confidence }}
          </span>
          <span class="tag">{{ batchStore.currentStudent.grade }}</span>
        </div>
      </div>

      <div class="detail-hero__aside">
        <div class="detail-score">
          <div class="detail-score__main">{{ batchStore.currentStudent.score }}</div>
          <div class="detail-score__sub">百分制 {{ batchStore.currentStudent.percentileScore }}</div>
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
          :disabled="batchStore.loading || !batchStore.currentStudent.finalResultId"
          @click="confirmCurrentStudent"
        >
          教师确认
        </button>
      </div>
    </article>

    <section class="panel review-summary-panel">
      <div class="review-summary-panel__headline">
        <div>
          <span class="eyebrow">复核摘要</span>
          <h3>{{ reviewRecommendation }}</h3>
        </div>
        <span class="status-badge" :class="reviewTone">{{ reviewRecommendation }}</span>
      </div>
      <div class="review-summary-grid">
        <article class="summary-item">
          <span>总分</span>
          <strong>{{ batchStore.currentStudent.score }} / {{ batchStore.currentStudent.percentileScore }}</strong>
        </article>
        <article class="summary-item">
          <span>置信度</span>
          <strong>{{ batchStore.currentStudent.confidence }}</strong>
        </article>
        <article class="summary-item">
          <span>未覆盖需求</span>
          <strong>{{ uncoveredCount }}</strong>
        </article>
        <article class="summary-item">
          <span>门禁状态</span>
          <strong>{{ gateSummary }}</strong>
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
          <span class="panel__subtle">先看结论，再决定是否深入核查</span>
        </div>
        <ul class="detail-list">
          <li v-for="item in batchStore.currentStudent.qualityFindings" :key="item">{{ item }}</li>
        </ul>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>改进建议</h3>
          <span class="panel__subtle">按维度汇总最值得反馈给学生的内容</span>
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
          <h3>维度得分</h3>
          <p class="panel__description">默认先展示得分、简述和操作建议，证据与推理折叠在卡片下方。</p>
        </div>
      </div>

      <div class="issue-stack">
        <article v-for="item in batchStore.currentStudent.dimensions" :key="item.id" class="dimension-summary-card">
          <div class="dimension-summary-card__top">
            <div>
              <h4>{{ item.name }}</h4>
              <p class="dimension-summary-card__meta">得分 {{ item.score }}/{{ item.maxScore }} · 置信度 {{ item.confidence }}</p>
            </div>
            <span class="pill">{{ scoreToneLabel(item.score, item.maxScore) }}</span>
          </div>

          <div class="content-grid content-grid--two">
            <article class="detail-list-card">
              <h4>主要证据</h4>
              <p>{{ item.evidence }}</p>
            </article>
            <article class="detail-list-card detail-list-card--risk">
              <h4>主要缺失</h4>
              <ul>
                <li v-for="miss in item.missing" :key="miss">{{ miss }}</li>
              </ul>
            </article>
          </div>

          <article class="detail-block">
            <h4>评分推理</h4>
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
          <span class="panel__subtle">查看需求覆盖与缺口</span>
        </div>

        <div class="traceability-grid traceability-grid--compact">
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

        <div class="alert-strip">
          <strong>未覆盖需求：</strong>
          <span>{{ batchStore.currentStudent.traceability.uncoveredRequirements.join("；") }}</span>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>门禁与材料摘要</h3>
          <span class="panel__subtle">辅助判断这份样本是否需要人工复核</span>
        </div>

        <div class="gate-grid">
          <article v-for="item in batchStore.currentStudent.gates" :key="item.name" class="gate-card">
            <div class="gate-card__top">
              <strong>{{ item.name }}</strong>
              <span class="status-badge" :class="item.passed ? 'status-badge--good' : 'status-badge--risk'">
                {{ item.passed ? "通过" : "未通过" }}
              </span>
            </div>
            <div class="gate-card__meta">{{ item.detail }}</div>
            <div class="gate-card__meta">on_fail: {{ item.onFail }}</div>
          </article>
        </div>

        <article class="detail-list-card">
          <h4>原始材料摘要</h4>
          <ul>
            <li>文档数：{{ batchStore.currentStudent.materials.documentCount }}</li>
            <li>字数：{{ batchStore.currentStudent.materials.wordCount }}</li>
            <li>图片数：{{ batchStore.currentStudent.materials.imageCount }}</li>
            <li>角色：{{ batchStore.currentStudent.materials.roles.join("；") }}</li>
            <li v-for="log in batchStore.currentStudent.materials.logs" :key="log">{{ log }}</li>
          </ul>
        </article>
      </section>
    </div>
  </section>

  <section v-else class="view">
    <section class="panel">
      <div class="empty-state">
        <h4>{{ batchStore.loading ? "正在加载样本解释" : "未找到该学生的样本解释" }}</h4>
        <p>
          {{
            batchStore.loading
              ? "系统正在读取学生评分详情，请稍候。"
              : "当前学生 ID 没有匹配到评分详情，可能是列表 ID 与详情结果文件未对齐。"
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
const uncoveredCount = computed(() => batchStore.currentStudent?.traceability.uncoveredRequirements.length ?? 0);
const gateSummary = computed(() => {
  const gates = batchStore.currentStudent?.gates ?? [];
  const failed = gates.filter((item) => !item.passed).length;
  return failed > 0 ? `${failed} 项未通过` : "全部通过";
});
const reviewRecommendation = computed(() => {
  const student = batchStore.currentStudent;
  if (!student) return "";
  if (student.gates.some((item) => !item.passed)) return "必须人工复核";
  if (student.confidence < 0.8 || uncoveredCount.value > 0) return "建议抽查复核";
  return "可直接通过";
});
const reviewTone = computed(() => {
  if (reviewRecommendation.value === "必须人工复核") return "status-badge--risk";
  if (reviewRecommendation.value === "建议抽查复核") return "status-badge--warn";
  return "status-badge--good";
});

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
