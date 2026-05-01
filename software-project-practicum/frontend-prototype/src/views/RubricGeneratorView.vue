<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">{{ baseRubric ? "基于现有标准生成副本" : "文本生成 Rubric" }}</div>
        <h2 class="hero-card__title">
          {{ baseRubric ? "先参考原标准，再描述你想调整的评分规则" : "先用自然语言生成草稿，再决定是否保存和绑定" }}
        </h2>
        <p class="hero-card__text">
          {{
            baseRubric
              ? "系统会保留原 Rubric 作为参考。你只需要说明哪些内容要保留、修改或新增，系统再生成新的结构化副本草稿。"
              : "左侧输入任务上下文和自然语言要求，右侧查看结构化摘要、YAML 预览和风险提示。"
          }}
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">目标总分 {{ taskStore.currentTask.score }}</span>
        <span v-if="baseRubric" class="pill">{{ baseRubric.name }}</span>
      </div>
    </div>

    <div class="content-grid content-grid--generator">
      <div class="detail-content">
        <section v-if="baseRubric" class="panel">
          <div class="panel__header">
            <h3>原标准参考</h3>
          </div>
          <div class="summary-grid">
            <div class="summary-item"><span>名称</span><strong>{{ baseRubric.name }}</strong></div>
            <div class="summary-item"><span>版本</span><strong>{{ baseRubric.version }}</strong></div>
            <div class="summary-item"><span>总分</span><strong>{{ baseRubric.totalScore }}</strong></div>
            <div class="summary-item"><span>维度数</span><strong>{{ baseRubric.dimensions.length }}</strong></div>
          </div>
          <div class="detail-list-card">
            <h4>关键维度</h4>
            <ul>
              <li v-for="item in baseRubric.dimensions" :key="item.id">{{ item.name }} · {{ item.maxScore }} 分</li>
            </ul>
          </div>
          <div v-if="baseRubric.warnings.length > 0" class="inline-alert inline-alert--warn">
            {{ baseRubric.warnings.join("；") }}
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>任务上下文</h3>
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
            <h3>{{ baseRubric ? "描述你希望基于当前标准做哪些调整" : "自然语言输入" }}</h3>
          </div>
          <textarea v-model="prompt" class="text-editor" rows="12"></textarea>
          <div class="tag-row">
            <span class="tag">可描述评分维度</span>
            <span class="tag">可描述分值调整</span>
            <span class="tag">可描述扣分规则</span>
            <span class="tag">可描述门禁要求</span>
          </div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>生成操作</h3>
          </div>
          <div class="toolbar__actions">
            <button class="action-button" :disabled="configStore.saving" @click="generate">
              {{ configStore.saving ? "生成中..." : baseRubric ? "生成副本草稿" : "生成 Rubric 草稿" }}
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
              {{ draftCanBind ? "可保存并绑定" : "建议先保存草稿" }}
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
          <div v-else class="empty-state">先生成草稿，再在右侧查看结构化摘要和 YAML 预览。</div>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>YAML 预览</h3>
          </div>
          <pre class="yaml-preview">{{ configStore.generatedDraft?.yaml ?? "# 尚未生成草稿" }}</pre>
        </section>

        <section class="panel">
          <div class="panel__header">
            <h3>风险提示</h3>
          </div>
          <ul v-if="configStore.generatedDraft" class="detail-list">
            <li v-for="item in configStore.generatedDraft.warnings" :key="item">{{ item }}</li>
          </ul>
          <div v-else class="empty-state">生成后这里会展示总分不闭合、门禁缺失或结构冲突等提示。</div>
          <div class="toolbar__actions">
            <button class="action-button" :disabled="!configStore.generatedDraft || configStore.saving" @click="saveDraft">保存为草稿</button>
            <button class="action-button action-button--ghost" :disabled="!draftCanBind || configStore.saving" @click="saveAndBind">
              绑定到当前任务
            </button>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const route = useRoute();
const router = useRouter();
const taskStore = useTaskContextStore();
const configStore = useConfigStore();

const basePrompt =
  "请按照需求规格说明书、概要设计说明书和详细设计说明书的承接关系评分。重点检查需求是否清晰、概要设计是否覆盖需求、详细设计是否继续承接，并关注模板残留、术语不一致、关键模块缺失等问题。总分 100 分，要求生成评分维度、扣分点、门禁规则和评语要求。";

const prompt = ref(basePrompt);

const baseRubric = computed(() => {
  const rubricId = route.query.baseRubricId ? String(route.query.baseRubricId) : "";
  return configStore.rubrics.find((item) => item.id === rubricId) ?? null;
});

const draftCanBind = computed(() => Boolean(configStore.generatedDraft?.canBind));

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
  () => baseRubric.value?.id,
  (rubricId) => {
    configStore.resetGeneratedDraft();
    if (!rubricId || !baseRubric.value) {
      prompt.value = basePrompt;
      return;
    }
    prompt.value = `请基于“${baseRubric.value.name} ${baseRubric.value.version}”生成一个新的评分标准副本。\n\n我希望保留的部分：${baseRubric.value.dimensions.map((item) => item.name).join("、")}。\n我希望调整的部分：请根据本次任务需求描述新的分值、扣分规则、门禁要求和评语要求。`;
  },
  { immediate: true },
);

const generate = async () => {
  await configStore.generateRubric(prompt.value, baseRubric.value);
};

const resetPrompt = () => {
  prompt.value = baseRubric.value
    ? `请基于“${baseRubric.value.name} ${baseRubric.value.version}”生成一个新的评分标准副本。\n\n我希望保留的部分：${baseRubric.value.dimensions.map((item) => item.name).join("、")}。\n我希望调整的部分：请根据本次任务需求描述新的分值、扣分规则、门禁要求和评语要求。`
    : basePrompt;
  configStore.resetGeneratedDraft();
};

const saveDraft = async () => {
  if (!taskStore.currentTask) return;
  const created = await configStore.saveGeneratedRubric(taskStore.currentTask.id, false);
  if (created) {
    await router.push({ name: "task-rubric-detail", params: { taskId: taskStore.currentTask.id, rubricId: created.id } });
  }
};

const saveAndBind = async () => {
  if (!taskStore.currentTask || !configStore.generatedDraft) return;
  const created = await configStore.saveGeneratedRubric(taskStore.currentTask.id, true);
  if (created) {
    await configStore.bindRubric(taskStore.currentTask.id, created.id);
    await router.push({ name: "task-rubric-detail", params: { taskId: taskStore.currentTask.id, rubricId: created.id } });
  }
};
</script>
