<template>
  <section class="view" v-if="taskStore.currentTask && workingTemplate">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">导出模板</div>
        <h2 class="hero-card__title">先保存模板，再绑定到当前任务</h2>
        <p class="hero-card__text">
          首发版本只开放 Excel 结果表配置。模板围绕“成绩总表、统计分析、评分明细”三个 sheet 展开，可配置字段开关和命名规则。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ workingTemplate.name }}</span>
        <span class="pill">{{ workingTemplate.version }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>模板基础信息</h3>
            <p class="panel__description">这里决定模板名称和最终导出文件的命名规则。</p>
          </div>
        </div>

        <div class="config-form-grid">
          <label class="field">
            <span>模板名称</span>
            <input v-model="workingTemplate.name" class="field__input" type="text" />
          </label>
          <label class="field">
            <span>文件命名规则</span>
            <input v-model="workingTemplate.fileNameRule" class="field__input" type="text" />
          </label>
        </div>

        <div class="inline-alert inline-alert--warn">当前仅支持 Excel 导出，其他格式入口暂不开放。</div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>模板动作</h3>
            <p class="panel__description">保存后再决定是否立即绑定到当前任务。</p>
          </div>
          <div class="toolbar__actions toolbar__actions--column">
            <button class="action-button" :disabled="configStore.saving" @click="saveTemplate">保存模板</button>
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="bindTemplate">绑定当前任务</button>
            <button class="action-button action-button--ghost" @click="previewFields">
              {{ showPreview ? "收起字段预览" : "预览字段" }}
            </button>
          </div>
        </div>
      </aside>
    </div>

    <section v-if="showPreview" class="panel">
      <div class="panel__header">
        <div>
          <h3>字段预览</h3>
          <p class="panel__description">按 sheet 查看当前启用的导出字段，便于快速确认模板结构。</p>
        </div>
      </div>
      <div class="config-card-stack">
        <article v-for="group in previewGroups" :key="group.sheetName" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ group.sheetName }}</div>
              <div class="rubric-card__meta">{{ group.enabledColumns.length }} / {{ group.totalColumns }} 个字段已启用</div>
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
          <h3>Sheet 配置</h3>
          <p class="panel__description">按 sheet 打开或关闭需要导出的字段。</p>
        </div>
      </div>
      <div class="config-card-stack">
        <article v-for="sheet in workingTemplate.sheets" :key="sheet.id" class="config-record-card">
          <div class="config-record-card__top">
            <label class="field field--inline">
              <span>Sheet 名称</span>
              <input v-model="sheet.name" class="field__input" type="text" />
            </label>
            <span class="pill">{{ sheet.columns.filter((item) => item.enabled).length }} / {{ sheet.columns.length }} 已启用</span>
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
const workingTemplate = ref<ExportTemplate | null>(null);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

watch(
  () => configStore.currentTemplate,
  (value) => {
    workingTemplate.value = value ? (JSON.parse(JSON.stringify(value)) as ExportTemplate) : null;
  },
  { immediate: true },
);

const previewGroups = computed(() =>
  workingTemplate.value?.sheets.map((sheet) => ({
    sheetName: sheet.name,
    totalColumns: sheet.columns.length,
    enabledColumns: sheet.columns.filter((item) => item.enabled).map((item) => item.label),
  })) ?? [],
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
</script>
