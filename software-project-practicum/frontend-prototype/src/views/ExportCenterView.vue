<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出中心</div>
        <h2 class="hero-card__title">成绩报表导出</h2>
        <p class="hero-card__text">
          系统会先执行导出前检查，并将每次真实导出写入导出记录，便于后续追踪导出时间、风险快照和生成结果。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="levelPillClass">{{ exportLevelLabel }}</span>
        <span class="pill">历史 {{ configStore.gradeExportRecords.length }} 条</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">总人数</div>
        <div class="stat-card__value">{{ precheckSummary.totalStudents }}</div>
      </article>
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">已评分</div>
        <div class="stat-card__value">{{ precheckSummary.gradedStudents }}</div>
      </article>
      <article class="stat-card" :class="precheckSummary.reviewRequiredStudents > 0 ? 'stat-card--warn' : 'stat-card--good'">
        <div class="stat-card__label">待确认</div>
        <div class="stat-card__value">{{ precheckSummary.reviewRequiredStudents }}</div>
      </article>
      <article class="stat-card" :class="precheckSummary.lowConfidenceStudents > 0 ? 'stat-card--warn' : 'stat-card--neutral'">
        <div class="stat-card__label">低置信度</div>
        <div class="stat-card__value">{{ precheckSummary.lowConfidenceStudents }}</div>
      </article>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>导出前检查</h3>
            <p class="panel__description">{{ exportConclusion }}</p>
          </div>
          <button class="action-button action-button--ghost" :disabled="configStore.loadingExportPrecheck" @click="reloadPrecheck">
            {{ configStore.loadingExportPrecheck ? "检查中..." : "重新检查" }}
          </button>
        </div>

        <div v-if="configStore.exportPrecheck" class="config-card-stack">
          <article class="config-record-card">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">检查结论：{{ exportLevelLabel }}</div>
                <div class="rubric-card__meta">{{ configStore.exportPrecheck.suggestedAction }}</div>
              </div>
            </div>
            <ul class="detail-list">
              <li>已提交学生：{{ precheckSummary.submittedStudents }}</li>
              <li>已评分学生：{{ precheckSummary.gradedStudents }}</li>
              <li>教师已确认：{{ precheckSummary.confirmedStudents }}</li>
              <li>评分失败：{{ precheckSummary.failedStudents }}</li>
              <li>缺失结果：{{ precheckSummary.missingResultStudents }}</li>
            </ul>
          </article>

          <article v-if="configStore.exportPrecheck.blockers.length > 0" class="inline-alert inline-alert--risk">
            <strong>阻断问题</strong>
            <ul>
              <li v-for="item in configStore.exportPrecheck.blockers" :key="`blocker-${item.type}`">{{ item.message }}</li>
            </ul>
          </article>

          <article v-if="configStore.exportPrecheck.warnings.length > 0" class="inline-alert inline-alert--warn">
            <strong>风险提示</strong>
            <ul>
              <li v-for="item in configStore.exportPrecheck.warnings" :key="`warning-${item.type}`">{{ item.message }}</li>
            </ul>
          </article>
        </div>
        <div v-else class="empty-state">尚未完成导出前检查。</div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>真实导出操作</h3>
            <p class="panel__description">导出将创建一条数据库记录，并调用真实报表生成脚本。</p>
          </div>
          <button class="action-button" :disabled="exportButtonDisabled" @click="createExport">
            {{ exportButtonText }}
          </button>
        </div>

        <article v-if="configStore.exportPrecheck?.exportLevel === 'WARN'" class="inline-alert inline-alert--warn">
          当前成绩可以导出，但存在风险。确认风险后允许继续导出，风险快照会写入导出记录。
        </article>
        <article v-if="configStore.exportPrecheck?.exportLevel === 'BLOCK'" class="inline-alert inline-alert--risk">
          当前任务暂不可导出，请先处理阻断问题。
        </article>

        <div v-if="configStore.lastExportResult" class="config-record-card">
          <div class="rubric-card__title">最近一次导出结果</div>
          <div class="rubric-card__meta">
            记录 #{{ configStore.lastExportResult.exportId ?? "-" }} · {{ exportResultStatusLabel }}
          </div>
          <p class="rubric-card__summary">
            {{ configStore.lastExportResult.report ? `已生成报表：${configStore.lastExportResult.report}` : configStore.lastExportResult.failedReason ?? "后端已触发导出。" }}
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
          <h3>真实导出历史</h3>
          <p class="panel__description">这里展示 grade_export_record 中的真实导出记录。下载仍是临时“最新报表”入口，尚未支持按 exportId 下载。</p>
        </div>
        <div class="toolbar__actions">
          <button class="action-button action-button--ghost" :disabled="configStore.loadingGradeExportRecords" @click="reloadRecords">
            {{ configStore.loadingGradeExportRecords ? "刷新中..." : "刷新历史" }}
          </button>
          <button class="action-button action-button--ghost" :disabled="configStore.saving || !latestCompletedRecord" @click="downloadLatestReport">
            下载最新报表
          </button>
        </div>
      </div>

      <div v-if="configStore.gradeExportRecords.length > 0" class="config-card-stack">
        <article v-for="item in configStore.gradeExportRecords" :key="item.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ item.fileName ?? "尚未生成文件" }}</div>
              <div class="rubric-card__meta">
                记录 #{{ item.id }} · {{ item.createdAt }} · 风险等级 {{ item.exportLevel ?? "-" }}
              </div>
            </div>
            <span class="status-badge" :class="statusClass(item.status)">
              {{ statusLabel(item.status) }}
            </span>
          </div>
          <ul class="detail-list">
            <li>总人数：{{ item.totalStudents }}，已评分：{{ item.gradedStudents }}</li>
            <li>待确认：{{ item.reviewRequiredStudents }}，低置信度：{{ item.lowConfidenceStudents }}</li>
            <li>风险数量：{{ item.warningCount }}，阻断数量：{{ item.blockerCount }}</li>
            <li v-if="item.completedAt">完成时间：{{ item.completedAt }}</li>
            <li v-if="item.status === 'FAILED' && item.failedReason">失败原因：{{ item.failedReason }}</li>
          </ul>
        </article>
      </div>
      <div v-else class="empty-state">当前任务还没有真实导出记录。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useBatchStore } from "../stores/batch";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import { useUiStore } from "../stores/ui";
import type { GradeExportStatus } from "../types";

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
        configStore.loadGradeExportPrecheck(taskId),
        configStore.loadGradeExportRecords(taskId),
        batchStore.loadResults(taskId),
        batchStore.loadProgress(taskId),
      ]);
    }
  },
  { immediate: true },
);

const emptySummary = {
  totalStudents: 0,
  submittedStudents: 0,
  gradedStudents: 0,
  confirmedStudents: 0,
  reviewRequiredStudents: 0,
  lowConfidenceStudents: 0,
  failedStudents: 0,
  missingResultStudents: 0,
};

const precheckSummary = computed(() => configStore.exportPrecheck?.summary ?? emptySummary);
const latestCompletedRecord = computed(() => configStore.gradeExportRecords.find((item) => item.status === "COMPLETED"));

const exportLevelLabel = computed(() => {
  if (!configStore.exportPrecheck) return "等待检查";
  const map = { PASS: "可以导出", WARN: "有风险", BLOCK: "暂不可导出" };
  return map[configStore.exportPrecheck.exportLevel] ?? configStore.exportPrecheck.exportLevel;
});

const levelPillClass = computed(() => {
  if (configStore.exportPrecheck?.exportLevel === "PASS") return "pill--good";
  if (configStore.exportPrecheck?.exportLevel === "BLOCK") return "pill--risk";
  return "pill--warn";
});

const exportConclusion = computed(() => {
  if (!configStore.exportPrecheck) return "正在等待导出前检查结果。";
  if (configStore.exportPrecheck.exportLevel === "PASS") return "当前成绩结果满足导出条件，可以直接导出。";
  if (configStore.exportPrecheck.exportLevel === "WARN") return "当前成绩可以导出，但存在风险，建议先复核。";
  return "当前任务暂不可导出，请先处理阻断问题。";
});

const exportButtonText = computed(() => {
  if (configStore.saving) return "导出中...";
  if (configStore.exportPrecheck?.exportLevel === "BLOCK") return "暂不可导出";
  if (configStore.exportPrecheck?.exportLevel === "WARN") return "确认风险并导出";
  return "导出 Excel";
});

const exportButtonDisabled = computed(() => configStore.saving || configStore.loadingExportPrecheck || configStore.exportPrecheck?.exportLevel === "BLOCK");
const exportResultStatusLabel = computed(() => configStore.lastExportResult?.status ? statusLabel(configStore.lastExportResult.status) : "已触发");

const reloadPrecheck = async () => {
  const taskId = taskStore.currentTask?.id;
  if (taskId) await configStore.loadGradeExportPrecheck(taskId);
};

const reloadRecords = async () => {
  const taskId = taskStore.currentTask?.id;
  if (taskId) await configStore.loadGradeExportRecords(taskId);
};

const createExport = async () => {
  const task = taskStore.currentTask;
  const precheck = configStore.exportPrecheck;
  if (!task?.assessmentId) {
    uiStore.pushToast("当前任务缺少 assessmentId，无法执行真实成绩导出。", "risk");
    return;
  }
  if (!precheck) {
    uiStore.pushToast("请先完成导出前检查。", "risk");
    return;
  }
  if (precheck.exportLevel === "BLOCK") return;
  if (precheck.exportLevel === "WARN") {
    const warningText = precheck.warnings.map((item) => item.message).join("\n");
    const confirmed = window.confirm(`当前导出存在以下风险：\n\n${warningText}\n\n确认风险并继续导出吗？`);
    if (!confirmed) return;
  }
  await configStore.startGradeExport();
};

const downloadLatestReport = async () => {
  await configStore.downloadLatestReport();
};

const statusLabel = (status: GradeExportStatus) => {
  const map = { PROCESSING: "导出中", COMPLETED: "已完成", FAILED: "失败" };
  return map[status] ?? status;
};

const statusClass = (status: GradeExportStatus) => {
  if (status === "COMPLETED") return "status-badge--good";
  if (status === "FAILED") return "status-badge--risk";
  return "status-badge--warn";
};
</script>
