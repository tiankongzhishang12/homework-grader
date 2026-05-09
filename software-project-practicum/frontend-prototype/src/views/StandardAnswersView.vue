<template>
  <section class="view answer-page-layout" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">标准答案</div>
        <h2 class="hero-card__title">标准答案管理</h2>
        <p class="hero-card__text">上传、解析并管理当前题目的标准答案版本，后续智能评分将基于当前标准答案执行。</p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill" :class="hasQuestion ? 'pill--good' : 'pill--warn'">题目{{ hasQuestion ? "已配置" : "未配置" }}</span>
        <span class="pill" :class="hasStandardAnswer ? 'pill--good' : 'pill--warn'">标准答案{{ hasStandardAnswer ? "已上传" : "未上传" }}</span>
      </div>
    </div>

    <section class="panel answer-overview-strip">
      <div class="answer-overview-strip__items">
        <div class="summary-item"><span>当前任务</span><strong>{{ taskStore.currentTask.taskName }}</strong></div>
        <div class="summary-item"><span>当前题目状态</span><strong>{{ hasQuestion ? "已配置" : "未配置" }}</strong></div>
        <div class="summary-item"><span>标准答案状态</span><strong>{{ hasStandardAnswer ? "已上传" : "未上传" }}</strong></div>
        <div class="summary-item"><span>已保存版本数</span><strong>{{ configStore.standardAnswers.length }}</strong></div>
        <div class="summary-item"><span>最新版本号</span><strong>{{ latestVersion }}</strong></div>
        <div class="summary-item"><span>最新保存时间</span><strong>{{ latestSavedAt }}</strong></div>
      </div>
      <details class="dev-debug-block">
        <summary>开发调试信息</summary>
        <div class="summary-grid">
          <div class="summary-item"><span>assessmentId</span><strong>{{ taskStore.currentTask.assessmentId ?? "缺失" }}</strong></div>
          <div class="summary-item"><span>templateId</span><strong>{{ taskStore.currentTask.templateId ?? "缺失" }}</strong></div>
          <div class="summary-item"><span>questionId</span><strong>{{ taskStore.currentTask.questionId ?? "缺失" }}</strong></div>
        </div>
      </details>
    </section>

    <section v-if="!hasQuestion" class="panel answer-warning-card">
      <div>
        <h3>当前任务还没有题目定义</h3>
        <p>标准答案必须绑定到具体题目。请先完成题目配置后再上传标准答案。</p>
      </div>
      <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initializeQuestion">自动补齐题目定义</button>
      <small>该操作仅用于 demo / 联调环境，正式系统中应由题目配置页面完成。</small>
    </section>

    <div class="answer-management-grid">
      <div class="answer-left-stack">
        <section class="panel answer-upload-card">
          <div class="panel__header">
            <div>
              <h3>上传标准答案</h3>
              <p class="panel__description">支持格式：.docx、.txt、.md、.json、.yaml、.yml、.csv。文件大小限制：20MB。</p>
            </div>
          </div>

          <label class="field">
            <span>选择标准答案文件</span>
            <input ref="fileInput" class="field__input" type="file" accept=".docx,.txt,.md,.json,.yaml,.yml,.csv" @change="selectAnswerFile" />
          </label>

          <div class="file-meta-row">
            <template v-if="selectedFile">
              <span>文件名：<strong>{{ selectedFile.name }}</strong></span>
              <span>文件大小：{{ configStore.formatFileSize(selectedFile.size) }}</span>
            </template>
            <span v-else>尚未选择文件</span>
          </div>

          <div class="answer-upload-actions">
            <button class="action-button" :disabled="configStore.saving || !hasQuestion || !selectedFile" @click="uploadSelectedAnswer">
              {{ configStore.saving ? "上传中..." : "上传并保存为新版本" }}
            </button>
          </div>
        </section>

        <details class="panel answer-manual-card">
          <summary>手动录入标准答案</summary>
          <div class="answer-manual-card__body">
            <p class="panel__description">适用于标准答案内容较短，或文件解析不稳定时直接粘贴文本。保存后会生成新的标准答案记录。</p>
            <label class="field">
              <span>标准答案文本</span>
              <textarea v-model="configStore.standardAnswerDraft" class="field__input field__input--textarea" rows="6" />
            </label>
            <div class="answer-manual-card__actions">
              <button class="action-button action-button--ghost" :disabled="configStore.saving || !hasQuestion" @click="saveAnswer">保存为文本版本</button>
            </div>
          </div>
        </details>
      </div>

      <aside class="panel answer-current-card">
        <div class="panel__header">
          <h3>当前标准答案摘要</h3>
        </div>
        <template v-if="hasStandardAnswer">
          <div class="summary-grid">
            <div class="summary-item"><span>最新版本</span><strong>{{ latestVersion }}</strong></div>
            <div class="summary-item"><span>保存时间</span><strong>{{ latestSavedAt }}</strong></div>
            <div class="summary-item"><span>版本数</span><strong>{{ configStore.standardAnswers.length }} 个</strong></div>
          </div>
          <div class="answer-current-preview">{{ latestSummary }}</div>
        </template>
        <div v-else class="answer-empty-state">当前题目还没有标准答案，请先上传文件或手动录入。</div>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>已保存记录</h3>
          <p class="panel__description">历史版本不会删除，便于教师追溯标准答案变更。</p>
        </div>
      </div>

      <div v-if="configStore.standardAnswers.length > 0" class="answer-version-list answer-version-list--compact">
        <article v-for="item in configStore.standardAnswers" :key="item.id" class="answer-version-row">
          <div class="answer-version-row__main">
            <strong>{{ versionTitle(item) }}</strong>
            <span class="answer-version-row__meta">
              保存时间 {{ item.created_at ?? item.updated_at ?? "暂无" }} · 状态 已保存
            </span>
            <p class="answer-version-summary">{{ configStore.formatStandardAnswerSummary(item) }}</p>
            <div v-if="expandedIds.has(String(item.id))" class="answer-version-fulltext">{{ fullAnswerText(item) }}</div>
          </div>
          <button class="action-button action-button--ghost" type="button" @click="toggleExpanded(String(item.id))">
            {{ expandedIds.has(String(item.id)) ? "收起全文" : "展开全文" }}
          </button>
        </article>
      </div>
      <div v-else class="answer-empty-state">当前题目还没有标准答案。请上传文件或手动录入标准答案。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import { useUiStore } from "../stores/ui";
import type { StandardAnswerRecord } from "../types";

const allowedExtensions = [".docx", ".txt", ".md", ".json", ".yaml", ".yml", ".csv"];
const maxFileSize = 20 * 1024 * 1024;

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const uiStore = useUiStore();
const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const expandedIds = ref(new Set<string>());

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const hasQuestion = computed(() => Boolean(taskStore.currentTask?.questionId));
const hasStandardAnswer = computed(() => configStore.standardAnswers.length > 0);
const latestAnswer = computed(() => configStore.getLatestStandardAnswer());
const latestVersion = computed(() => configStore.formatStandardAnswerVersion(latestAnswer.value));
const latestSavedAt = computed(() => latestAnswer.value?.created_at ?? latestAnswer.value?.updated_at ?? "暂无");
const latestSummary = computed(() => configStore.formatStandardAnswerSummary(latestAnswer.value));

const initializeQuestion = async () => {
  if (!taskStore.currentTask) return;
  await configStore.initializeTemplateAndQuestion(taskStore.currentTask.id);
};

const saveAnswer = async () => {
  if (!taskStore.currentTask) return;
  if (!configStore.standardAnswerDraft.trim()) {
    uiStore.pushToast("请先输入标准答案文本。", "risk");
    return;
  }
  if (!window.confirm("确认将当前文本保存为新的标准答案版本吗？")) return;
  await configStore.saveStandardAnswer(taskStore.currentTask.id);
};

const selectAnswerFile = (event: Event) => {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
};

const validateSelectedFile = () => {
  if (!selectedFile.value) {
    uiStore.pushToast("请先选择标准答案文件。", "risk");
    return false;
  }
  const lowerName = selectedFile.value.name.toLowerCase();
  if (!allowedExtensions.some((ext) => lowerName.endsWith(ext))) {
    uiStore.pushToast("文件格式不支持，请上传 .docx、.txt、.md、.json、.yaml、.yml 或 .csv 文件。", "risk");
    return false;
  }
  if (selectedFile.value.size > maxFileSize) {
    uiStore.pushToast("文件超过 20MB，请压缩或拆分后再上传。", "risk");
    return false;
  }
  return true;
};

const uploadSelectedAnswer = async () => {
  if (!taskStore.currentTask || !validateSelectedFile() || !selectedFile.value) return;
  const confirmed = window.confirm("确认上传该文件并保存为新的标准答案版本吗？历史版本不会删除，但后续评分可能会使用最新标准答案。");
  if (!confirmed) return;
  await configStore.uploadStandardAnswerFile(taskStore.currentTask.id, selectedFile.value);
  selectedFile.value = null;
  if (fileInput.value) fileInput.value.value = "";
};

const versionTitle = (item: StandardAnswerRecord) =>
  item.version_no ? `标准答案版本 v${item.version_no}` : `标准答案版本 #${item.id}`;

const fullAnswerText = (item: StandardAnswerRecord) => String(item.answer_text ?? item.answer_json ?? "无文本内容");

const toggleExpanded = (id: string) => {
  const next = new Set(expandedIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedIds.value = next;
};
</script>
