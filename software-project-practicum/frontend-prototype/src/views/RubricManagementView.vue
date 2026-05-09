<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">Rubric</div>
        <h2 class="hero-card__title">先准备 assessment template，再手动保存 Rubric JSON 或 YAML</h2>
        <p class="hero-card__text">
          第一版不走模型生成，老师可以直接粘贴 Rubric 内容并保存到真实 `/api/templates/{templateId}/rubrics`。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ taskStore.currentTask.templateId ?? "未初始化 templateId" }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>保存真实 Rubric</h3>
            <p class="panel__description">支持手动粘贴 JSON 或 YAML。若缺少 `templateId`，请先初始化 assessment template。</p>
          </div>
          <div class="toolbar__actions">
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initializeQuestion">
              初始化题目定义
            </button>
            <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.templateId" @click="saveRubric">
              {{ configStore.saving ? "保存中..." : "保存 Rubric" }}
            </button>
          </div>
        </div>

        <div v-if="!taskStore.currentTask.templateId" class="inline-alert inline-alert--warn">
          请先初始化 assessment template。
        </div>

        <label class="field">
          <span>Rubric JSON / YAML</span>
          <textarea v-model="rubricDraft" class="field__input field__input--textarea" rows="16" />
        </label>
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
            <span>当前 Rubric</span>
            <strong>{{ configStore.currentRubric?.name ?? "未保存" }}</strong>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const rubricDraft = ref(`rubric_id: homework-grader-demo
total_score: 100
dimensions:
  - name: Correctness
    max_score: 60
  - name: Completeness
    max_score: 40
`);

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

const saveRubric = async () => {
  if (!taskStore.currentTask) return;
  await configStore.saveRubricDefinition(taskStore.currentTask.id, rubricDraft.value);
};
</script>
