<template>
  <section class="view" v-if="taskStore.currentTask && configStore.currentTemplate">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出中心</div>
        <h2 class="hero-card__title">导出前先看风险提示，再决定是否继续</h2>
        <p class="hero-card__text">
          系统会先展示当前模板版本、异常学生数和质量提示，再由老师决定是否继续导出 Excel。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ configStore.currentTemplate.version }}</span>
        <span class="pill">{{ exportVerdict }}</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">总人数</div>
        <div class="stat-card__value">{{ batchStore.analytics?.totalStudents ?? taskStore.currentTask.studentCount }}</div>
      </article>
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">已完成评分</div>
        <div class="stat-card__value">{{ batchStore.progress?.completed ?? taskStore.currentTask.submittedCount }}</div>
      </article>
      <article class="stat-card" :class="exportRiskStudentCount > 0 ? 'stat-card--warn' : 'stat-card--good'">
        <div class="stat-card__label">异常学生数</div>
        <div class="stat-card__value">{{ exportRiskStudentCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">风险命中次数</div>
        <div class="stat-card__value">{{ riskHitCount }}</div>
      </article>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>当前模板摘要</h3>
            <p class="panel__description">按 sheet 查看当前导出模板中已启用的字段。</p>
          </div>
          <button class="action-button action-button--ghost" @click="togglePreview">
            {{ showPreview ? "收起字段预览" : "预览导出字段" }}
          </button>
        </div>

        <div class="config-card-stack">
          <article v-for="sheet in configStore.currentTemplate.sheets" :key="sheet.id" class="config-record-card">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">{{ sheet.name }}</div>
                <div class="rubric-card__meta">{{ sheet.columns.filter((item) => item.enabled).length }} 个字段已启用</div>
              </div>
            </div>
            <div class="tag-row">
              <span v-for="column in sheet.columns.filter((item) => item.enabled)" :key="column.id" class="tag">{{ column.label }}</span>
            </div>
          </article>
        </div>

        <div v-if="showPreview" class="config-card-stack">
          <article v-for="group in previewGroups" :key="group.sheetName" class="config-record-card">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">{{ group.sheetName }}</div>
                <div class="rubric-card__meta">{{ group.enabledColumns.length }} 个字段</div>
              </div>
            </div>
            <div v-if="group.enabledColumns.length > 0" class="tag-row">
              <span v-for="column in group.enabledColumns" :key="column" class="tag">{{ column }}</span>
            </div>
            <div v-else class="empty-state empty-state--small">当前 sheet 暂未启用字段。</div>
          </article>
        </div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>质量提示</h3>
            <p class="panel__description">这些提示不会阻断导出，但会影响老师是否需要先复核样本。</p>
          </div>
          <button class="action-button" :disabled="batchStore.loading" @click="createExport">
            {{ batchStore.loading ? "导出中..." : "导出 Excel" }}
          </button>
        </div>

        <article v-if="exportRiskStudentCount > 0" class="inline-alert inline-alert--warn">
          当前有 {{ exportRiskStudentCount }} 名学生需要关注，导出前建议先完成抽查或确认。
        </article>

        <ul class="detail-list">
          <li>低置信度学生：{{ lowConfidenceStudentCount }}</li>
          <li>模板残留学生：{{ placeholderResidueStudentCount }}</li>
          <li>门禁异常学生：{{ gateWarningStudentCount }}</li>
        </ul>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>导出历史</h3>
      </div>
      <div v-if="batchStore.exports.length > 0" class="config-card-stack">
        <article v-for="item in batchStore.exports" :key="item.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ item.fileName }}</div>
              <div class="rubric-card__meta">{{ item.createdAt }} · 模板 {{ item.templateVersion }}</div>
            </div>
            <span class="status-badge" :class="item.status === 'completed' ? 'status-badge--good' : item.status === 'failed' ? 'status-badge--risk' : 'status-badge--warn'">
              {{ exportStatusLabel(item.status) }}
            </span>
          </div>
          <div class="tag-row">
            <span v-for="warning in item.warnings" :key="warning" class="tag tag--warn">{{ warning }}</span>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">暂无导出历史。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useBatchStore } from "../stores/batch";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import type { StudentRow } from "../types";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const batchStore = useBatchStore();
const showPreview = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await Promise.all([
        configStore.loadTaskConfig(taskId),
        batchStore.loadResults(taskId),
        batchStore.loadExports(taskId),
        batchStore.loadProgress(taskId),
      ]);
    }
  },
  { immediate: true },
);

const hasExportRisk = (student: StudentRow) =>
  student.confidence < 0.8 || student.traceabilityGapCount > 0 || student.consistencyIssueCount > 0 || student.gateStatus !== "通过";

const hasLowConfidenceRisk = (student: StudentRow) => student.confidence < 0.8;
const hasPlaceholderRisk = (student: StudentRow) => student.riskTags.some((tag) => tag.includes("残留") || tag.includes("占位"));
const hasGateRisk = (student: StudentRow) => student.gateStatus !== "通过";

const exportRiskStudentCount = computed(() => batchStore.students.filter(hasExportRisk).length);
const lowConfidenceStudentCount = computed(() => batchStore.students.filter(hasLowConfidenceRisk).length);
const placeholderResidueStudentCount = computed(() => batchStore.students.filter(hasPlaceholderRisk).length);
const gateWarningStudentCount = computed(() => batchStore.students.filter(hasGateRisk).length);

const riskHitCount = computed(
  () =>
    lowConfidenceStudentCount.value +
    placeholderResidueStudentCount.value +
    gateWarningStudentCount.value +
    batchStore.students.filter((student) => student.traceabilityGapCount > 0 || student.consistencyIssueCount > 0).length,
);

const previewGroups = computed(() =>
  configStore.currentTemplate?.sheets.map((sheet) => ({
    sheetName: sheet.name,
    enabledColumns: sheet.columns.filter((item) => item.enabled).map((item) => item.label),
  })) ?? [],
);

const exportVerdict = computed(() => {
  if (gateWarningStudentCount.value > 0) return "建议先处理门禁异常";
  if (exportRiskStudentCount.value > 0) return "建议抽查风险学生";
  return "可以直接导出";
});

const exportStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    processing: "处理中",
    completed: "已完成",
    failed: "失败",
  };
  return map[status] ?? status;
};

const togglePreview = () => {
  showPreview.value = !showPreview.value;
};

const createExport = async () => {
  if (!taskStore.currentTask) return;
  if (exportRiskStudentCount.value > 0) {
    const confirmed = window.confirm(
      `当前有 ${exportRiskStudentCount.value} 名风险学生，仍要继续导出吗？\n\n低置信度：${lowConfidenceStudentCount.value}\n模板残留：${placeholderResidueStudentCount.value}\n门禁异常：${gateWarningStudentCount.value}`,
    );
    if (!confirmed) return;
  }
  await batchStore.createExport(taskStore.currentTask.id);
};
</script>
