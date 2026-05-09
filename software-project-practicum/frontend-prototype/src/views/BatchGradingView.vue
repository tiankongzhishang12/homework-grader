<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">批量阅卷</div>
        <h2 class="hero-card__title">自动阅卷执行台</h2>
        <p class="hero-card__text">
          当前页面用于启动和跟踪自动阅卷任务。系统会使用当前已保存的评分标准，对学生提交进行预处理、大模型评分和结果导入。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill" :class="taskStore.canStartBatch ? 'pill--good' : 'pill--warn'">
          {{ taskStore.canStartBatch ? "配置已满足执行条件" : "当前仍有阻断项" }}
        </span>
        <span class="pill">{{ progressLabel }}</span>
      </div>
    </div>

    <div class="batch-summary-grid">
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">阅卷状态</div>
        <div class="stat-card__value stat-card__value--small">{{ progressLabel }}</div>
      </article>
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">评分进度</div>
        <div class="stat-card__value stat-card__value--small">{{ progressText }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">使用 Rubric</div>
        <div class="stat-card__value stat-card__value--small">{{ runtimeRubric?.rubricRuntimeId ?? "开始后加载" }}</div>
      </article>
      <article class="stat-card" :class="qualityIssueCount > 0 ? 'stat-card--warn' : 'stat-card--good'">
        <div class="stat-card__label">待处理事项</div>
        <div class="stat-card__value">{{ qualityIssueCount }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>执行操作</h3>
          <p class="panel__description">进度会自动刷新；页面隐藏时暂停轮询，返回后继续。</p>
        </div>
        <div class="toolbar__actions">
          <button class="action-button" :disabled="primaryDisabled" @click="startIncremental">
            {{ primaryButtonLabel }}
          </button>
          <button class="action-button action-button--ghost" :disabled="batchStore.loading || isRunning" @click="startFull">
            重新批改全部
          </button>
          <button class="action-button action-button--ghost" :disabled="batchStore.refreshingProgress" @click="refreshProgress">
            {{ batchStore.refreshingProgress ? "刷新中..." : "刷新状态" }}
          </button>
          <button class="action-button action-button--ghost" :disabled="batchStore.refreshingLogs" @click="loadLogs">
            {{ batchStore.refreshingLogs ? "刷新中..." : "刷新技术日志" }}
          </button>
          <RouterLink :to="{ name: 'task-analysis', params: { taskId: taskStore.currentTask.id } }" class="action-button action-button--ghost">
            进入结果分析
          </RouterLink>
        </div>
      </div>

      <div class="batch-refresh-meta">
        <span>本次模式：{{ gradingModeLabel }}</span>
        <span>状态最后刷新：{{ formatRefreshTime(batchStore.lastProgressRefreshedAt) }}</span>
        <span>日志最后刷新：{{ formatRefreshTime(batchStore.lastLogsRefreshedAt) }}</span>
      </div>

      <article class="detail-block detail-block--highlight">
        <h4>当前步骤</h4>
        <p>{{ batchStore.progress?.currentStepLabel ?? "等待开始阅卷。" }}</p>
      </article>

      <div class="inline-alert" :class="checklist.ready ? 'inline-alert--good' : 'inline-alert--warn'">
        {{ checklist.message }}
      </div>
    </section>

    <div class="content-grid content-grid--two">
      <section class="panel batch-rubric-card">
        <div class="panel__header">
          <h3>当前使用评分标准</h3>
        </div>
        <div v-if="runtimeRubric" class="summary-grid summary-grid--compact">
          <div class="summary-item">
            <span>Rubric 名称</span>
            <strong>{{ runtimeRubric.rubricName ?? "未命名 Rubric" }}</strong>
          </div>
          <div class="summary-item">
            <span>Rubric ID</span>
            <strong>{{ runtimeRubric.rubricRuntimeId }}</strong>
          </div>
          <div class="summary-item">
            <span>数据库 ID</span>
            <strong>{{ runtimeRubric.rubricDefinitionId ?? "-" }}</strong>
          </div>
          <div class="summary-item">
            <span>来源</span>
            <strong>教师确认保存的评分标准</strong>
          </div>
          <details class="dev-debug-block">
            <summary>运行时 YAML 路径</summary>
            <p>{{ runtimeRubric.rubricYamlPath }}</p>
          </details>
        </div>
        <div v-else class="batch-rubric-empty">
          开始阅卷后，系统会自动加载当前任务已保存的评分标准。
        </div>
      </section>

      <section class="panel batch-quality-card">
        <div class="panel__header">
          <h3>待处理事项</h3>
        </div>
        <div v-if="qualityIssueCount === 0" class="batch-quality-empty">
          <strong>暂无待处理质量风险。</strong>
          <p>本次阅卷未发现导入失败、评分失败或进度异常。</p>
        </div>
        <div v-else class="issue-stack">
          <article v-for="item in qualityItems" :key="item.key" class="issue-card issue-card--warn">
            <div class="issue-card__title">{{ item.label }}</div>
            <div class="issue-card__detail">{{ item.detail }}</div>
          </article>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>执行进度</h3>
      </div>
      <div class="batch-timeline">
        <article
          v-for="step in executionSteps"
          :key="step.key"
          class="batch-timeline-item"
          :class="`batch-timeline-item--${step.status}`"
        >
          <div class="batch-timeline-item__dot"></div>
          <div>
            <div class="batch-timeline-item__title">
              <strong>{{ step.label }}</strong>
              <span>{{ stepStatusLabel(step.status) }}</span>
            </div>
            <p>{{ step.detail }}</p>
          </div>
        </article>
      </div>
    </section>

    <details class="panel technical-log-panel">
      <summary>技术日志（用于排查脚本、模型调用和导入异常）</summary>
      <ul class="technical-log-list">
        <li
          v-for="(item, index) in batchStore.logs"
          :key="`log-${index}-${item.time}`"
          class="technical-log-item"
          :class="`technical-log-item--${item.level}`"
        >
          <span>[{{ item.level }}]</span>
          <time>{{ item.time }}</time>
          <p>{{ item.message }}</p>
        </li>
      </ul>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from "vue";
import { RouterLink } from "vue-router";
import { useBatchStore } from "../stores/batch";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import { useUiStore } from "../stores/ui";

const taskStore = useTaskContextStore();
const batchStore = useBatchStore();
const configStore = useConfigStore();
const uiStore = useUiStore();

const progressLabel = computed(() => {
  const map: Record<string, string> = {
    idle: "待开始",
    preprocessing: "预处理中",
    scoring: "评分中",
    aggregating: "汇总中",
    completed: "已完成",
    failed: "失败",
  };
  return map[batchStore.progress?.status ?? taskStore.currentTask?.batchStatus ?? "idle"];
});

const runtimeRubric = computed(() => batchStore.progress?.runtimeRubric);
const qualitySummary = computed(() => batchStore.progress?.qualitySummary);
const qualityIssueCount = computed(() => qualitySummary.value?.totalIssues ?? 0);
const progressText = computed(() => `${batchStore.progress?.completed ?? 0} / ${batchStore.progress?.total ?? taskStore.currentTask?.submittedCount ?? 0}`);
const isRunning = computed(() => ["preprocessing", "scoring", "aggregating"].includes(batchStore.progress?.status ?? ""));
const isCompleted = computed(() => batchStore.progress?.status === "completed");
const isFailed = computed(() => batchStore.progress?.status === "failed");
const checklist = computed(() => configStore.configChecklist(taskStore.currentTask?.id ?? ""));
const primaryButtonLabel = computed(() => {
  if (isRunning.value) return "阅卷进行中...";
  return "批改新增/更新提交";
});
const primaryDisabled = computed(() => !taskStore.canStartBatch || batchStore.loading || isRunning.value);
const executionSteps = computed(() => batchStore.progress?.executionSteps ?? []);
const gradingModeLabel = computed(() => {
  const mode = batchStore.progress?.gradingMode;
  if (mode === "FULL") return "全量重批";
  if (mode === "INCREMENTAL") return "增量阅卷";
  return "尚未开始";
});

const qualityItems = computed(() => {
  const summary = qualitySummary.value;
  if (!summary) return [];
  const items: Array<{ key: string; label: string; detail: string }> = [];
  if ((summary.importSkippedCount ?? 0) > 0) items.push({ key: "import-skipped", label: "结果导入跳过", detail: `${summary.importSkippedCount} 个结果被跳过` });
  if ((summary.importFailedCount ?? 0) > 0) items.push({ key: "import-failed", label: "结果导入失败", detail: `${summary.importFailedCount} 个结果导入失败` });
  if ((summary.scriptFailedCount ?? 0) > 0) items.push({ key: "script-failed", label: "评分失败", detail: `${summary.scriptFailedCount} 份学生提交评分失败` });
  if (summary.progressStalled) items.push({ key: "progress-stalled", label: "进度停滞", detail: "脚本进度长时间未更新" });
  if ((summary.needsReviewCount ?? 0) > 0) items.push({ key: "needs-review", label: "需人工复核", detail: `${summary.needsReviewCount} 个结果需要复核` });
  if ((summary.lowConfidenceCount ?? 0) > 0) items.push({ key: "low-confidence", label: "低置信度", detail: `${summary.lowConfidenceCount} 个分项置信度偏低` });
  return items;
});

const syncVisibility = async () => {
  if (!taskStore.currentTask) return;
  if (document.visibilityState === "visible" && isRunning.value) {
    await batchStore.loadProgress(taskStore.currentTask.id, true);
  } else if (document.visibilityState === "hidden") {
    batchStore.stopPolling();
  }
};

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
      await batchStore.loadProgress(taskId, true);
      await batchStore.loadLogs(taskId);
    }
  },
  { immediate: true },
);

document.addEventListener("visibilitychange", syncVisibility);

onUnmounted(() => {
  document.removeEventListener("visibilitychange", syncVisibility);
  batchStore.stopPolling();
});

const startIncremental = async () => {
  if (!taskStore.currentTask) return;
  if (!checklist.value.ready) {
    window.alert(checklist.value.message);
    return;
  }
  await batchStore.startBatch(taskStore.currentTask.id, "INCREMENTAL");
};

const startFull = async () => {
  if (!taskStore.currentTask) return;
  if (!checklist.value.ready) {
    window.alert(checklist.value.message);
    return;
  }
  const confirmed = window.confirm("当前任务已有评分结果。重新批改全部会再次调用大模型，并更新已有学生成绩。请确认是否继续？");
  if (!confirmed) return;
  await batchStore.startBatch(taskStore.currentTask.id, "FULL");
};

const refreshProgress = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.loadProgress(taskStore.currentTask.id, true);
  uiStore.pushToast("状态已刷新");
};

const loadLogs = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.loadLogs(taskStore.currentTask.id);
  uiStore.pushToast("技术日志已刷新");
};

const stepStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: "待执行",
    running: "执行中",
    completed: "已完成",
    failed: "失败",
    warning: "需注意",
  };
  return map[status] ?? status;
};

const formatRefreshTime = (value: string | null) => {
  if (!value) return "尚未刷新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
};
</script>
