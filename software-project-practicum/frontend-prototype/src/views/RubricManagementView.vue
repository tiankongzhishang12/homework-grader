<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">Rubric</div>
        <h2 class="hero-card__title">添加评分标准</h2>
        <p class="hero-card__text">
          老师可以用中文描述评分规则，系统会调用大模型生成结构化 Rubric JSON 草稿。草稿经教师确认后才会保存并用于后续评分。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ taskStore.currentTask.score }} 分</span>
      </div>
    </div>

    <section class="panel rubric-status-strip">
      <div class="rubric-status-strip__items">
        <div class="summary-item">
          <span>当前任务</span>
          <strong>{{ taskStore.currentTask.taskName }}</strong>
        </div>
        <div class="summary-item">
          <span>任务总分</span>
          <strong>{{ taskStore.currentTask.score }} 分</strong>
        </div>
        <div class="summary-item">
          <span>Assessment Template</span>
          <strong>{{ taskStore.currentTask.templateId ? "已配置" : "未配置" }}</strong>
        </div>
        <div class="summary-item">
          <span>当前 Rubric</span>
          <strong>{{ configStore.currentRubric ? "已保存" : "未保存" }}</strong>
        </div>
      </div>
      <details class="dev-debug-block">
        <summary>开发调试信息</summary>
        <div class="summary-grid summary-grid--compact">
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
        </div>
      </details>
    </section>

    <div v-if="!taskStore.currentTask.templateId" class="inline-alert inline-alert--warn">
      当前任务还没有 assessment template。请先初始化题目定义后再生成评分标准。
      <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initializeQuestion">
        自动补齐题目定义
      </button>
    </div>

    <div class="rubric-compiler-grid">
      <section class="panel rubric-input-card">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>中文评分标准</h3>
            <p class="panel__description">按自然语言说明评分项、分值、封顶规则和需要人工复核的情况。</p>
          </div>
        </div>
        <label class="field">
          <span>评分标准描述</span>
          <textarea v-model="teacherText" class="field__input field__input--textarea" rows="16" />
        </label>
        <div class="rubric-input-hint">
          建议写清楚满分、每个评分维度的分值、证据要求、扣分规则、封顶规则和人工复核条件。
        </div>
        <div class="toolbar__actions">
          <button class="action-button" :disabled="compileDisabled" @click="compileRubric">
            {{ configStore.saving ? "生成中..." : "生成结构化草稿" }}
          </button>
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="clearTeacherText">
            清空输入
          </button>
        </div>

        <details class="rubric-advanced-block">
          <summary>高级：直接粘贴 JSON/YAML</summary>
          <p class="panel__description">该入口用于调试或高级用户直接保存结构化 Rubric，不会调用大模型。</p>
          <label class="field">
            <span>Rubric JSON / YAML</span>
            <textarea v-model="manualRubricText" class="field__input field__input--textarea" rows="10" />
          </label>
          <div class="toolbar__actions toolbar__actions--right">
            <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.templateId" @click="saveManualRubric">
              保存 Rubric
            </button>
          </div>
        </details>
      </section>

      <aside class="panel rubric-preview-card">
        <div class="panel__header">
          <h3>生成结果预览</h3>
        </div>

        <div v-if="!compiledRubric" class="rubric-preview-empty">
          请先在左侧输入中文评分标准，然后点击“生成结构化草稿”。
        </div>

        <template v-else>
          <div class="rubric-preview-head">
            <div>
              <span>Rubric 名称</span>
              <strong>{{ compiledRubric.rubricName || "未命名 Rubric" }}</strong>
            </div>
            <div>
              <span>总分</span>
              <strong>{{ compiledRubric.totalScore }} 分</strong>
            </div>
            <span class="pill" :class="compiledRubric.canSave ? 'pill--good' : 'pill--risk'">
              {{ compiledRubric.canSave ? "可保存" : "需调整" }}
            </span>
          </div>

          <div v-if="compiledRubric.warnings.length" class="rubric-warning-list">
            <strong>风险提示</strong>
            <ul>
              <li v-for="warning in compiledRubric.warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>

          <div class="rubric-dimension-list">
            <article v-for="dimension in compiledRubric.dimensions" :key="dimension.code || dimension.name" class="rubric-dimension-card">
              <div class="rubric-dimension-card__title">
                <strong>{{ dimension.name }}</strong>
                <span>{{ dimension.maxScore }} 分</span>
              </div>
              <p>{{ dimension.description }}</p>
              <div v-if="dimension.evidenceRequirements.length" class="rubric-chip-row">
                <span v-for="item in dimension.evidenceRequirements" :key="item">{{ item }}</span>
              </div>
            </article>
          </div>

          <div v-if="compiledRubric.capRules.length" class="rubric-rule-block">
            <strong>封顶规则</strong>
            <p v-for="rule in compiledRubric.capRules" :key="`${rule.condition}-${rule.capScore}`">
              {{ rule.condition }}：最高 {{ rule.capScore }} 分<span v-if="rule.reason">，{{ rule.reason }}</span>
            </p>
          </div>

          <div v-if="compiledRubric.reviewFlags.length" class="rubric-rule-block">
            <strong>人工复核规则</strong>
            <p v-for="flag in compiledRubric.reviewFlags" :key="`${flag.condition}-${flag.action}`">
              {{ flag.condition }}：{{ flag.action }}
            </p>
          </div>

          <div class="rubric-save-actions">
            <button class="action-button" :disabled="configStore.saving || !compiledRubric.canSave" @click="saveCompiledRubric">
              保存评分标准
            </button>
            <button class="action-button action-button--ghost" @click="copyJson">复制 JSON</button>
            <button class="action-button action-button--ghost" :disabled="compileDisabled" @click="compileRubric">重新生成</button>
          </div>

          <div>
            <h4>JSON 预览</h4>
            <pre class="rubric-json-preview">{{ compiledRubricJson }}</pre>
          </div>
        </template>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import { useUiStore } from "../stores/ui";

const defaultTeacherText = `需求规格说明书满分100分。
1. 系统目标与范围20分：说明系统目标、使用场景、用户范围和系统边界。
2. 用户角色与用例分析20分：列出主要参与者、核心用例和角色权限。
3. 业务流程分析20分：给出主要业务流程，可使用文字、流程图或表格说明。
4. 数据设计20分：说明主要数据对象、字段和关系。
5. 非功能需求20分：说明安全性、性能、可用性和可维护性。
如果没有需求规格说明书正文，最高不超过40分。
如果证据矛盾或无法判断，需要人工复核。`;

const manualRubricSample = `{
  "rubric_name": "需求规格说明书评分标准",
  "total_score": 100,
  "dimensions": [],
  "cap_rules": [],
  "review_flags": [],
  "warnings": []
}`;

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const uiStore = useUiStore();
const teacherText = ref(configStore.rubricTeacherText || defaultTeacherText);
const manualRubricText = ref(manualRubricSample);

const compiledRubric = computed(() => configStore.compiledRubric);
const compileDisabled = computed(
  () => configStore.saving || !taskStore.currentTask?.templateId || !teacherText.value.trim(),
);
const compiledRubricJson = computed(() =>
  compiledRubric.value ? JSON.stringify(compiledRubric.value.rubricJson, null, 2) : "",
);

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

const compileRubric = async () => {
  if (!taskStore.currentTask) return;
  await configStore.compileRubricFromText(taskStore.currentTask.id, teacherText.value);
};

const clearTeacherText = () => {
  teacherText.value = "";
  configStore.rubricTeacherText = "";
};

const saveCompiledRubric = async () => {
  if (!taskStore.currentTask) return;
  const confirmed = window.confirm("确认保存该评分标准吗？保存后将作为当前任务的 Rubric 配置来源之一。");
  if (!confirmed) return;
  await configStore.saveCompiledRubric(taskStore.currentTask.id);
};

const saveManualRubric = async () => {
  if (!taskStore.currentTask) return;
  await configStore.saveRubricDefinition(taskStore.currentTask.id, manualRubricText.value);
};

const copyJson = async () => {
  if (!compiledRubricJson.value) return;
  await navigator.clipboard.writeText(compiledRubricJson.value);
  uiStore.pushToast("Rubric JSON 已复制。");
};
</script>
