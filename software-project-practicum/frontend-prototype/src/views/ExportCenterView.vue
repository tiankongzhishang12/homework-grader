<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出中心</div>
        <h2 class="hero-card__title">成绩报表导出</h2>
        <p class="hero-card__text">
          当前阶段使用真实成绩导出接口，根据 assessmentId 触发后端报表生成。导出成功后可下载最近生成的报表。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="taskStore.currentTask.assessmentId ? 'pill--good' : 'pill--warn'">
          {{ taskStore.currentTask.assessmentId ? "真实导出已就绪" : "缺少 assessmentId" }}
        </span>
        <span v-if="configStore.currentTemplate" class="pill">{{ configStore.currentTemplate.version }}</span>
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
        <div class="stat-card__label">需关注学生</div>
        <div class="stat-card__value">{{ exportRiskStudentCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">最近导出</div>
        <div class="stat-card__value stat-card__value--small">{{ latestReportLabel }}</div>
      </article>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>当前导出模板</h3>
            <p class="panel__description">第一阶段继续沿用现有模板配置展示，主导出链路已切换到真实成绩导出接口。</p>
          </div>
          <button v-if="configStore.currentTemplate" class="action-button action-button--ghost" @click="togglePreview">
            {{ showPreview ? "收起字段预览" : "预览导出字段" }}
          </button>
        </div>

        <div v-if="configStore.currentTemplate" class="config-card-stack">
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
        <div v-else class="empty-state">当前任务尚未配置导出模板，仍可尝试真实成绩导出。</div>

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
            <h3>真实导出操作</h3>
            <p class="panel__description">点击后调用 POST /api/assessments/{assessmentId}/grades/export。</p>
          </div>
          <button class="action-button" :disabled="configStore.saving" @click="createExport">
            {{ configStore.saving ? "导出中..." : "导出 Excel" }}
          </button>
        </div>

        <article v-if="exportRiskStudentCount > 0" class="inline-alert inline-alert--warn">
          当前有 {{ exportRiskStudentCount }} 名学生存在低置信度、复核或质量风险。第一阶段不阻断导出，请按需要先到结果分析页复核。
        </article>

        <ul class="detail-list">
          <li>低置信度学生：{{ lowConfidenceStudentCount }}</li>
          <li>模板残留风险：{{ placeholderResidueStudentCount }}</li>
          <li>复核/门禁异常：{{ gateWarningStudentCount }}</li>
        </ul>

        <div v-if="configStore.lastExportResult" class="config-record-card">
          <div class="rubric-card__title">最近一次真实导出结果</div>
          <div class="rubric-card__meta">assessmentId {{ configStore.lastExportResult.assessmentId ?? taskStore.currentTask.assessmentId }}</div>
          <p class="rubric-card__summary">
            {{ configStore.lastExportResult.report ? `已生成报表：${configStore.lastExportResult.report}` : "后端已触发导出，暂未返回报表文件名。" }}
          </p>
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="downloadLatestReport">
            下载最新报表
          </button>
        </div>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>临时导出结果</h3>
          <p class="panel__description">第一阶段不再读取 demo 导出历史。这里仅展示本页面最近一次真实导出触发结果。</p>
        </div>
        <button class="action-button action-button--ghost" :disabled="configStore.saving || !configStore.lastExportResult" @click="downloadLatestReport">
          下载最新报表
        </button>
      </div>
      <div v-if="configStore.lastExportResult" class="config-card-stack">
        <article class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ configStore.lastExportResult.report ?? "真实导出任务已触发" }}</div>
              <div class="rubric-card__meta">assessmentId {{ configStore.lastExportResult.assessmentId ?? taskStore.currentTask.assessmentId }}</div>
            </div>
            <span class="status-badge status-badge--good">已触发</span>
          </div>
          <p class="rubric-card__summary">下载入口暂时使用“最新报表”接口，后续会切换为按 exportId 下载。</p>
        </article>
      </div>
      <div v-else class="empty-state">尚未在本页面触发真实成绩导出。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useBatchStore } from "../stores/batch";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import { useUiStore } from "../stores/ui";
import type { StudentRow } from "../types";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const batchStore = useBatchStore();
const uiStore = useUiStore();
const showPreview = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await Promise.all([
        configStore.loadTaskConfig(taskId),
        batchStore.loadResults(taskId),
        batchStore.loadProgress(taskId),
      ]);
    }
  },
  { immediate: true },
);

const isGatePass = (value: string) => ["通过", "PASS", "PASSED", "passed"].includes(value);
const hasExportRisk = (student: StudentRow) =>
  student.confidence < 0.8 || student.traceabilityGapCount > 0 || student.consistencyIssueCount > 0 || !isGatePass(student.gateStatus);

const hasLowConfidenceRisk = (student: StudentRow) => student.confidence < 0.8;
const hasPlaceholderRisk = (student: StudentRow) => student.riskTags.some((tag) => tag.includes("残留") || tag.includes("占位"));
const hasGateRisk = (student: StudentRow) => !isGatePass(student.gateStatus);

const exportRiskStudentCount = computed(() => batchStore.students.filter(hasExportRisk).length);
const lowConfidenceStudentCount = computed(() => batchStore.students.filter(hasLowConfidenceRisk).length);
const placeholderResidueStudentCount = computed(() => batchStore.students.filter(hasPlaceholderRisk).length);
const gateWarningStudentCount = computed(() => batchStore.students.filter(hasGateRisk).length);

const latestReportLabel = computed(() => configStore.lastExportResult?.report ?? "暂无");

const previewGroups = computed(() =>
  configStore.currentTemplate?.sheets.map((sheet) => ({
    sheetName: sheet.name,
    enabledColumns: sheet.columns.filter((item) => item.enabled).map((item) => item.label),
  })) ?? [],
);

const togglePreview = () => {
  showPreview.value = !showPreview.value;
};

const createExport = async () => {
  const task = taskStore.currentTask;
  if (!task?.assessmentId) {
    uiStore.pushToast("当前任务缺少 assessmentId，无法执行真实成绩导出。", "risk");
    return;
  }
  if (exportRiskStudentCount.value > 0) {
    const confirmed = window.confirm(
      `当前有 ${exportRiskStudentCount.value} 名学生存在导出前风险，仍要继续导出吗？\n\n低置信度：${lowConfidenceStudentCount.value}\n模板残留：${placeholderResidueStudentCount.value}\n复核/门禁异常：${gateWarningStudentCount.value}`,
    );
    if (!confirmed) return;
  }
  await configStore.startGradeExport();
};

const downloadLatestReport = async () => {
  await configStore.downloadLatestReport();
};
</script>
