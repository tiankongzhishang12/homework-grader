<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">标准答案</div>
        <h2 class="hero-card__title">上传标准答案文件，系统自动保存为答案版本</h2>
        <p class="hero-card__text">
          老师优先上传 .docx、.txt、.md、.json、.yaml 或 .csv 标准答案文件；解析后的正文会写入真实标准答案表。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ taskStore.currentTask.questionId ?? "未初始化 questionId" }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>上传标准答案</h3>
            <p class="panel__description">
              若当前任务还没有 questionId，请先初始化题目定义。上传后端会解析文件正文，并保存到
              `/api/questions/{questionId}/standard-answers/upload`。
            </p>
          </div>
          <div class="toolbar__actions">
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initializeQuestion">
              初始化题目定义
            </button>
            <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.questionId || !selectedFile" @click="uploadSelectedAnswer">
              {{ configStore.saving ? "上传中..." : "上传标准答案" }}
            </button>
          </div>
        </div>

        <div v-if="!taskStore.currentTask.questionId" class="inline-alert inline-alert--warn">
          请先初始化题目定义。
        </div>

        <label class="field">
          <span>标准答案文件</span>
          <input class="field__input" type="file" accept=".docx,.txt,.md,.json,.yaml,.yml,.csv" @change="selectAnswerFile" />
        </label>

        <div v-if="selectedFile" class="inline-alert inline-alert--good">
          已选择：{{ selectedFile.name }}
        </div>

        <details class="detail-block">
          <summary>临时文本录入</summary>
          <label class="field">
            <span>标准答案文本</span>
            <textarea v-model="configStore.standardAnswerDraft" class="field__input field__input--textarea" rows="12" />
          </label>
          <button class="action-button action-button--ghost" :disabled="configStore.saving || !taskStore.currentTask.questionId" @click="saveAnswer">
            保存文本版本
          </button>
        </details>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>当前状态</h3>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span>assessmentId</span>
            <strong>{{ taskStore.currentTask.assessmentId ?? "缺失" }}</strong>
          </div>
          <div class="summary-item">
            <span>templateId</span>
            <strong>{{ taskStore.currentTask.templateId ?? "缺失" }}</strong>
          </div>
          <div class="summary-item">
            <span>questionId</span>
            <strong>{{ taskStore.currentTask.questionId ?? "缺失" }}</strong>
          </div>
          <div class="summary-item">
            <span>记录数</span>
            <strong>{{ configStore.standardAnswers.length }}</strong>
          </div>
        </div>

        <article class="detail-block detail-block--highlight">
          <h4>最新标准答案</h4>
          <p>{{ configStore.summarizeStandardAnswer() }}</p>
        </article>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>已保存记录</h3>
          <p class="panel__description">展示当前 questionId 下已经保存的标准答案版本。</p>
        </div>
      </div>

      <div v-if="configStore.standardAnswers.length > 0" class="config-card-stack">
        <article v-for="item in configStore.standardAnswers" :key="item.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">Standard Answer #{{ item.id }}</div>
              <div class="rubric-card__meta">version {{ item.version_no ?? "-" }} | {{ item.created_at ?? item.updated_at ?? "-" }}</div>
            </div>
          </div>
          <p class="rubric-card__summary">{{ item.answer_text ?? item.answer_json ?? "无文本内容" }}</p>
        </article>
      </div>
      <div v-else class="empty-state">当前题目还没有标准答案记录。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const selectedFile = ref<File | null>(null);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const initializeQuestion = async () => {
  if (!taskStore.currentTask) return;
  await configStore.initializeTemplateAndQuestion(taskStore.currentTask.id);
};

const saveAnswer = async () => {
  if (!taskStore.currentTask) return;
  await configStore.saveStandardAnswer(taskStore.currentTask.id);
};

const selectAnswerFile = (event: Event) => {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
};

const uploadSelectedAnswer = async () => {
  if (!taskStore.currentTask || !selectedFile.value) return;
  await configStore.uploadStandardAnswerFile(taskStore.currentTask.id, selectedFile.value);
  selectedFile.value = null;
};
</script>
