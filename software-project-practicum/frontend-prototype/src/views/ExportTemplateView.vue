<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出模板与成绩导出</div>
        <h2 class="hero-card__title">模板展示先保留，真实主线先打通导出与下载</h2>
        <p class="hero-card__text">
          第一版不做完整模板 CRUD。当前页面继续展示原型模板，同时增加真实 `/api/assessments/{assessmentId}/grades/export` 和 `/api/reports/latest/download` 操作。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ configStore.currentTemplate?.name ?? "原型模板" }}</span>
        <span class="pill">{{ taskStore.currentTask.assessmentId ?? "缺少 assessmentId" }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>真实导出操作</h3>
            <p class="panel__description">先触发导出，再下载最新报表。</p>
          </div>
          <div class="toolbar__actions">
            <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.assessmentId" @click="startExport">
              {{ configStore.saving ? "处理中..." : "导出成绩" }}
            </button>
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="downloadLatest">
              下载最新报表
            </button>
          </div>
        </div>

        <article class="detail-block detail-block--highlight">
          <h4>最近一次导出</h4>
          <p>{{ exportSummary }}</p>
        </article>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>当前模板展示</h3>
        </div>
        <div v-if="configStore.currentTemplate" class="config-summary-stack">
          <article class="detail-block detail-block--highlight">
            <h4>{{ configStore.currentTemplate.name }}</h4>
            <p>{{ configStore.currentTemplate.version }} | {{ configStore.currentTemplate.fileNameRule }}</p>
          </article>
        </div>
        <div v-else class="empty-state empty-state--small">当前仍沿用原型模板展示。</div>
      </aside>
    </div>

    <section class="panel" v-if="configStore.currentTemplate">
      <div class="panel__header">
        <div>
          <h3>原型模板字段</h3>
          <p class="panel__description">这部分仍保留现有展示，不作为真实主链路阻断项。</p>
        </div>
      </div>
      <div class="config-card-stack">
        <article v-for="sheet in configStore.currentTemplate.sheets" :key="sheet.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ sheet.name }}</div>
              <div class="rubric-card__meta">{{ sheet.columns.filter((item) => item.enabled).length }} / {{ sheet.columns.length }} 已启用</div>
            </div>
          </div>
          <div class="tag-row">
            <span v-for="column in sheet.columns.filter((item) => item.enabled)" :key="column.id" class="tag">{{ column.label }}</span>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const exportSummary = computed(() => {
  if (!configStore.lastExportResult) return "还没有触发真实导出。";
  return configStore.lastExportResult.report
    ? `最近一次生成报表：${configStore.lastExportResult.report}`
    : "最近一次导出已触发，但后端未返回报表文件名。";
});

const startExport = async () => {
  await configStore.startGradeExport();
};

const downloadLatest = async () => {
  await configStore.downloadLatestReport();
};
</script>
