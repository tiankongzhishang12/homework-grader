<template>
  <section class="view" v-if="taskStore.currentTask && configStore.currentTemplate">
    <div class="hero-card">
      <div>
        <div class="eyebrow">导出中心</div>
        <h2 class="hero-card__title">导出前先展示质量提示，但不强制阻断教师导出</h2>
        <p class="hero-card__text">
          当前导出策略固定为“明显警告但允许导出”。系统会展示当前模板版本、异常样本数和质量提示摘要，同时把这些提示写入导出历史。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">模板：{{ configStore.currentTemplate.version }}</span>
        <span class="pill">仅支持 Excel</span>
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
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">异常样本数</div>
        <div class="stat-card__value">{{ warningCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">模板版本</div>
        <div class="stat-card__value stat-card__value--small">{{ configStore.currentTemplate.version }}</div>
      </article>
    </div>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>当前 Excel 模板字段</h3>
        </div>
        <div class="issue-stack">
          <article v-for="sheet in configStore.currentTemplate.sheets" :key="sheet.id" class="dimension-editor-card">
            <div class="dimension-editor-card__top">
              <strong>{{ sheet.name }}</strong>
              <span class="pill">{{ sheet.columns.filter((item) => item.enabled).length }} 列</span>
            </div>
            <div class="tag-row">
              <span v-for="column in sheet.columns.filter((item) => item.enabled)" :key="column.id" class="tag">{{ column.label }}</span>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>质量提示</h3>
        </div>
        <ul class="detail-list">
          <li>当前批次存在 {{ batchStore.analytics?.lowConfidenceCount ?? 0 }} 份低置信度样本。</li>
          <li>当前批次存在 {{ batchStore.analytics?.placeholderResidueCount ?? 0 }} 份模板残留样本。</li>
          <li>当前批次存在 {{ batchStore.analytics?.gateWarningCount ?? 0 }} 份门禁异常样本。</li>
        </ul>
        <div class="toolbar__actions">
          <button class="action-button action-button--ghost" @click="togglePreview">{{ showPreview ? "收起字段预览" : "预览导出字段" }}</button>
          <button class="action-button" :disabled="batchStore.loading" @click="createExport">
            {{ batchStore.loading ? "导出中..." : "导出 Excel" }}
          </button>
        </div>
        <article v-if="showPreview" class="detail-block detail-block--highlight">
          <h4>字段预览</h4>
          <p>{{ fieldSummary }}</p>
        </article>
      </section>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>导出历史</h3>
      </div>
      <div class="table-shell">
        <table class="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>文件名</th>
              <th>模板版本</th>
              <th>状态</th>
              <th>质量提示摘要</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in batchStore.exports" :key="item.id">
              <td>{{ item.createdAt }}</td>
              <td>{{ item.fileName }}</td>
              <td>{{ item.templateVersion }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.warnings.join("；") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useBatchStore } from "../stores/batch";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

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

const warningCount = computed(
  () => (batchStore.analytics?.lowConfidenceCount ?? 0) + (batchStore.analytics?.placeholderResidueCount ?? 0) + (batchStore.analytics?.gateWarningCount ?? 0),
);

const fieldSummary = computed(() =>
  configStore.currentTemplate?.sheets
    .map((sheet) => `${sheet.name}：${sheet.columns.filter((item) => item.enabled).map((item) => item.label).join("、")}`)
    .join("；") ?? "",
);

const togglePreview = () => {
  showPreview.value = !showPreview.value;
};

const createExport = async () => {
  if (!taskStore.currentTask) return;
  await batchStore.createExport(taskStore.currentTask.id);
};
</script>
