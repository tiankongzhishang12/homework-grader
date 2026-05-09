<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出中心</div>
        <h2 class="hero-card__title">成绩报表导出</h2>
        <p class="hero-card__text">
          系统会先执行导出前检查，统一判断当前任务是否可以导出、有哪些风险以及是否需要先复核。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="levelPillClass">{{ exportLevelLabel }}</span>
        <span v-if="configStore.currentTemplate" class="pill">{{ configStore.currentTemplate.version }}</span>
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

          <article v-if="configStore.exportPrecheck.blockers.length === 0 && configStore.exportPrecheck.warnings.length === 0" class="inline-alert inline-alert--good">
            当前成绩结果满足导出条件，可以直接导出。
          </article>
        </div>
        <div v-else class="empty-state">尚未完成导出前检查。</div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>真实导出操作</h3>
            <p class="panel__description">导出仍调用 POST /api/assessments/{assessmentId}/grades/export。</p>
          </div>
          <button class="action-button" :disabled="exportButtonDisabled" @click="createExport">
            {{ exportButtonText }}
          </button>
        </div>

        <article v-if="configStore.exportPrecheck?.exportLevel === 'WARN'" class="inline-alert inline-alert--warn">
          当前成绩可以导出，但存在风险。确认风险后允许继续导出。
        </article>
        <article v-if="configStore.exportPrecheck?.exportLevel === 'BLOCK'" class="inline-alert inline-alert--risk">
          当前任务暂不可导出，请先处理阻断问题。
        </article>

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
          <h3>当前导出模板</h3>
          <p class="panel__description">模板展示仍沿用现有配置；导出风险判断以后端 precheck 为准。</p>
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
      <div v-else class="empty-state">当前任务尚未配置导出模板，仍可在检查通过后尝试真实成绩导出。</div>

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

const exportLevelLabel = computed(() => {
  if (!configStore.exportPrecheck) return "等待检查";
  const map = {
    PASS: "可以导出",
    WARN: "有风险",
    BLOCK: "暂不可导出",
  };
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

const previewGroups = computed(() =>
  configStore.currentTemplate?.sheets.map((sheet) => ({
    sheetName: sheet.name,
    enabledColumns: sheet.columns.filter((item) => item.enabled).map((item) => item.label),
  })) ?? [],
);

const togglePreview = () => {
  showPreview.value = !showPreview.value;
};

const reloadPrecheck = async () => {
  const taskId = taskStore.currentTask?.id;
  if (taskId) await configStore.loadGradeExportPrecheck(taskId);
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
</script>
