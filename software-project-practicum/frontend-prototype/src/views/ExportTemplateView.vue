<template>
  <section class="view" v-if="taskStore.currentTask && workingTemplate">
    <div class="hero-card">
      <div>
        <div class="eyebrow">Excel 结果表格式设置</div>
        <h2 class="hero-card__title">仅支持 Excel，模板必须先保存并绑定到当前任务</h2>
        <p class="hero-card__text">
          首发版本只开放 Excel 结果表配置，不提供 CSV、PDF 或 Word 导出。模板围绕“成绩总表、统计分析、评分明细”三个 sheet 展开，可配置列开关、列顺序、sheet 名称和文件命名规则。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">{{ workingTemplate.name }}</span>
        <span class="pill">{{ workingTemplate.version }}</span>
      </div>
    </div>

    <div class="content-grid content-grid--two">
      <section class="panel">
        <div class="panel__header">
          <h3>模板基础信息</h3>
        </div>
        <label class="field">
          <span>模板名称</span>
          <input v-model="workingTemplate.name" class="field__input" type="text" />
        </label>
        <label class="field">
          <span>文件命名规则</span>
          <input v-model="workingTemplate.fileNameRule" class="field__input" type="text" />
        </label>
        <div class="inline-alert inline-alert--warn">仅支持 Excel 导出，当前模板不会提供其他导出格式入口。</div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <h3>模板动作</h3>
        </div>
        <div class="toolbar__actions toolbar__actions--column">
          <button class="action-button" :disabled="configStore.saving" @click="saveTemplate">保存模板</button>
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="bindTemplate">绑定当前任务</button>
          <button class="action-button action-button--ghost" @click="previewFields">预览字段</button>
        </div>
        <article v-if="showPreview" class="detail-block detail-block--highlight">
          <h4>字段预览</h4>
          <p>{{ enabledFieldSummary }}</p>
        </article>
      </section>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>Sheet 配置</h3>
      </div>
      <div class="issue-stack">
        <article v-for="sheet in workingTemplate.sheets" :key="sheet.id" class="dimension-editor-card">
          <div class="dimension-editor-card__top">
            <label class="field field--inline">
              <span>Sheet 名称</span>
              <input v-model="sheet.name" class="field__input" type="text" />
            </label>
            <span class="pill">{{ sheet.columns.filter((item) => item.enabled).length }} / {{ sheet.columns.length }} 列</span>
          </div>
          <div class="sheet-column-list">
            <label v-for="column in sheet.columns" :key="column.id" class="check-item">
              <input v-model="column.enabled" type="checkbox" />
              <span>{{ column.label }}</span>
            </label>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import type { ExportTemplate } from "../types";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const showPreview = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const workingTemplate = ref<ExportTemplate | null>(null);

watch(
  () => configStore.currentTemplate,
  (value) => {
    workingTemplate.value = value ? JSON.parse(JSON.stringify(value)) as ExportTemplate : null;
  },
  { immediate: true },
);

const saveTemplate = async () => {
  if (!taskStore.currentTask || !workingTemplate.value) return;
  await configStore.saveTemplate(taskStore.currentTask.id, workingTemplate.value);
};

const bindTemplate = async () => {
  if (!taskStore.currentTask || !workingTemplate.value?.id) return;
  await configStore.bindTemplate(taskStore.currentTask.id, workingTemplate.value.id);
};

const previewFields = () => {
  showPreview.value = !showPreview.value;
};

const enabledFieldSummary = computed(() =>
  workingTemplate.value?.sheets
    .map((sheet) => `${sheet.name}：${sheet.columns.filter((item) => item.enabled).map((item) => item.label).join("、")}`)
    .join("；"),
);
</script>
