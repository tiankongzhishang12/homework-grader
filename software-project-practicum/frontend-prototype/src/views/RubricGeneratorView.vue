<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">文本生成 Rubric</div>
        <h2 class="hero-card__title">自然语言先生成草稿，再决定是否保存并绑定到当前任务</h2>
        <p class="hero-card__text">
          页面采用双栏四步流：左侧输入任务上下文、自然语言描述和生成参数，右侧查看结构化摘要、YAML 预览和风险提示。只有结构完整的草稿才允许绑定当前任务。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">目标总分：{{ taskStore.currentTask.score }}</span>
      </div>
    </div>

    <div class="content-grid content-grid--generator">
      <div class="detail-content">
        <section class="panel">
          <div class="panel__header">
            <h3>1. 任务上下文</h3>
          </div>
          <div class="summary-grid">
            <div class="summary-item"><span>课程</span><strong>{{ taskStore.currentTask.courseName }}</strong></div>
            <div class="summary-item"><span>班级</span><strong>{{ taskStore.currentTask.className }}</strong></div>
            <div class="summary-item"><span>任务类型</span><strong>{{ taskStore.currentTask.taskType }}</strong></div>
            <div class="summary-item"><span>总分</span><strong>{{ taskStore.currentTask.score }}</strong></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>2. 自然语言输入</h3>
          </div>
          <textarea v-model="prompt" class="text-editor" rows="12"></textarea>
          <div class="tag-row">
            <span class="tag">建议描述评分维度</span>
            <span class="tag">建议描述分值</span>
            <span class="tag">建议描述门禁规则</span>
            <span class="tag">建议描述评语要求</span>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>3. 生成参数</h3>
          </div>
          <div class="filter-toolbar">
            <div class="select-mock"><span class="select-mock__label">生成模式</span><strong>严格模式</strong></div>
            <div class="select-mock"><span class="select-mock__label">Rubric 类型</span><strong>追踪评分</strong></div>
            <div class="select-mock"><span class="select-mock__label">输出细度</span><strong>维度 + 扣分点 + 门禁规则</strong></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>4. 生成操作</h3>
          </div>
          <div class="toolbar__actions">
            <button class="action-button" :disabled="configStore.saving" @click="generate">
              {{ configStore.saving ? "生成中..." : "生成 Rubric 初稿" }}
            </button>
            <button class="action-button action-button--ghost" @click="resetPrompt">清空输入</button>
          </div>
        </section>
      </div>

      <div class="detail-content">
        <section class="panel">
          <div class="panel__header">
            <h3>结构化摘要</h3>
            <span class="status-badge" :class="draftCanBind ? 'status-badge--good' : 'status-badge--warn'">
              {{ draftCanBind ? "可直接绑定" : "需先修正" }}
            </span>
          </div>
          <div v-if="configStore.generatedDraft" class="issue-stack">
            <article class="dimension-editor-card" v-for="item in configStore.generatedDraft.dimensions" :key="item.id">
              <div class="dimension-editor-card__top">
                <strong>{{ item.name }}</strong>
                <span class="pill">{{ item.maxScore }} 分</span>
              </div>
              <p>{{ item.description }}</p>
            </article>
          </div>
          <div v-else class="empty-state">先生成 Rubric 初稿，再在右侧查看结构化摘要和 YAML 预览。</div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>YAML 预览</h3>
          </div>
          <pre class="yaml-preview">{{ configStore.generatedDraft?.yaml ?? "# 尚未生成草稿" }}</pre>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>风险提示与映射对照</h3>
          </div>
          <ul v-if="configStore.generatedDraft" class="detail-list">
            <li v-for="item in configStore.generatedDraft.warnings" :key="item">{{ item }}</li>
          </ul>
          <div v-else class="empty-state">生成后这里会显示总分不闭合、门禁缺失或结构冲突等提示。</div>
          <div class="toolbar__actions">
            <button class="action-button" :disabled="!configStore.generatedDraft || configStore.saving" @click="saveDraft">
              保存为草稿
            </button>
            <button class="action-button action-button--ghost" :disabled="!draftCanBind || configStore.saving" @click="saveAndBind">
              绑定当前任务
            </button>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();

const prompt = ref(
  "请按需求规格说明书、概要设计说明书和详细设计说明书的承接关系评分。重点看需求是否清楚、概设是否覆盖需求、详设是否继续承接，并检查模板残留、术语不一致、关键模块缺失等问题。总分 100 分，要求生成维度评分、扣分点、门禁规则和评语要求。",
);

const draftCanBind = computed(() => Boolean(configStore.generatedDraft?.canBind));

const generate = async () => {
  await configStore.generateRubric(prompt.value);
};

const resetPrompt = () => {
  prompt.value = "";
  configStore.generatedDraft = null;
};

const saveDraft = async () => {
  if (!taskStore.currentTask) return;
  await configStore.saveGeneratedRubric(taskStore.currentTask.id, false);
};

const saveAndBind = async () => {
  if (!taskStore.currentTask || !configStore.generatedDraft) return;
  await configStore.saveGeneratedRubric(taskStore.currentTask.id, true);
  if (configStore.currentRubric) {
    await configStore.bindRubric(taskStore.currentTask.id, configStore.currentRubric.id);
  }
};
</script>
