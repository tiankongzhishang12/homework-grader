<template>
  <section class="view" v-if="taskStore.currentTask && rubric">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">Rubric 详情</div>
        <h2 class="hero-card__title">{{ rubric.name }}</h2>
        <p class="hero-card__text">
          先看当前标准的结构完整性和与任务的匹配度，再决定直接绑定，还是基于它生成新的草稿副本。
        </p>
        <div class="tag-row">
          <span class="pill">{{ rubric.version }}</span>
          <span class="pill">{{ sourceLabel(rubric.source) }}</span>
          <span class="pill">{{ statusLabel(rubric.status) }}</span>
          <span class="pill">{{ rubric.totalScore }} 分</span>
        </div>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="matchClassMap[matchLevel]">{{ matchLabelMap[matchLevel] }}</span>
        <span v-if="rubric.id === configStore.currentRubric?.id" class="pill pill--good">当前任务已绑定</span>
      </div>
    </div>

    <section class="panel panel--flat">
      <div class="course-workspace-toolbar">
        <RouterLink :to="{ name: 'task-rubrics', params: { taskId: taskStore.currentTask.id } }" class="action-button action-button--ghost">
          返回评分标准
        </RouterLink>
        <RouterLink
          :to="{ name: 'task-rubric-generator', params: { taskId: taskStore.currentTask.id }, query: { baseRubricId: rubric.id } }"
          class="action-button action-button--ghost"
        >
          基于此标准生成副本
        </RouterLink>
        <button v-if="canDeleteCopy" class="action-button action-button--ghost" :disabled="configStore.saving" @click="deleteCopy">
          删除副本
        </button>
        <button class="action-button" :disabled="configStore.saving || rubric.id === configStore.currentRubric?.id" @click="bindRubric">
          {{ rubric.id === configStore.currentRubric?.id ? "当前已绑定" : "绑定到当前任务" }}
        </button>
      </div>
    </section>

    <div class="stats-grid">
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">评分维度数</div>
        <div class="stat-card__value">{{ rubric.dimensions.length }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">总分</div>
        <div class="stat-card__value">{{ rubric.totalScore }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">风险提示</div>
        <div class="stat-card__value">{{ rubric.warnings.length }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">最近更新</div>
        <div class="stat-card__value stat-card__value--small">{{ rubric.updatedAt }}</div>
      </article>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>当前任务匹配判断</h3>
          <p class="panel__description">{{ taskStore.currentTask.taskName }} · {{ taskStore.currentTask.taskType }}</p>
        </div>
        <span class="pill" :class="matchClassMap[matchLevel]">{{ matchLabelMap[matchLevel] }}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>适用课程</span><strong>{{ taskStore.currentTask.courseName }}</strong></div>
        <div class="summary-item"><span>当前绑定状态</span><strong>{{ rubric.id === configStore.currentRubric?.id ? "已绑定到当前任务" : "尚未绑定" }}</strong></div>
        <div class="summary-item"><span>最近使用任务</span><strong>{{ rubric.lastUsedTaskName ?? "暂无记录" }}</strong></div>
        <div class="summary-item"><span>创建方式</span><strong>{{ sourceLabel(rubric.source) }}</strong></div>
      </div>
    </section>

    <section class="panel" :class="{ 'panel--risk': qualityFindings.length > 0 }">
      <div class="panel__header">
        <div>
          <h3>规则质量提示</h3>
          <p class="panel__description">帮助老师快速判断这个标准是否存在结构性问题或适配风险。</p>
        </div>
      </div>
      <div v-if="qualityFindings.length > 0" class="issue-stack">
        <article v-for="item in qualityFindings" :key="item" class="issue-card issue-card--warn">
          <div class="issue-card__title">{{ item }}</div>
        </article>
      </div>
      <div v-else class="inline-alert inline-alert--good">未发现明显结构性问题，可以作为当前任务候选标准。</div>
    </section>

    <section class="panel">
      <div class="panel__header panel__header--stack">
        <div>
          <h3>评分维度详情</h3>
          <p class="panel__description">可切换为只看关键规则模式，快速浏览每个维度的主要约束。</p>
        </div>
        <label class="check-item">
          <input v-model="keyRulesOnly" type="checkbox" />
          <span>只看关键规则</span>
        </label>
      </div>
      <div class="issue-stack">
        <article v-for="dimension in rubric.dimensions" :key="dimension.id" class="dimension-editor-card">
          <div class="dimension-editor-card__top">
            <strong>{{ dimension.name }}</strong>
            <span class="pill">{{ dimension.maxScore }} 分</span>
          </div>
          <p><strong>评分说明：</strong>{{ dimension.description }}</p>
          <template v-if="keyRulesOnly">
            <div class="detail-blocks">
              <article class="detail-block">
                <h4>关键扣分点</h4>
                <p>{{ deductionText(dimension.name) }}</p>
              </article>
              <article class="detail-block detail-block--highlight">
                <h4>门禁/风险提示</h4>
                <p>{{ gateText(dimension.name) }}</p>
              </article>
            </div>
          </template>
          <template v-else>
            <div class="detail-blocks">
              <article class="detail-block">
                <h4>评分关注点</h4>
                <p>{{ dimension.description }}</p>
              </article>
              <article class="detail-block">
                <h4>扣分规则</h4>
                <p>{{ deductionText(dimension.name) }}</p>
              </article>
              <article class="detail-block detail-block--highlight">
                <h4>风险标记条件</h4>
                <p>{{ gateText(dimension.name) }}</p>
              </article>
              <article class="detail-block">
                <h4>评语要求</h4>
                <p>{{ commentText(dimension.name) }}</p>
              </article>
            </div>
          </template>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>结构化预览</h3>
          <p class="panel__description">默认先看表单视图，YAML 仅用于核对结构化原文。</p>
        </div>
        <div class="tag-row">
          <button class="tag-button" :disabled="viewMode === 'form'" @click="viewMode = 'form'">表单视图</button>
          <button class="tag-button" :disabled="viewMode === 'yaml'" @click="viewMode = 'yaml'">YAML 视图</button>
        </div>
      </div>
      <div v-if="viewMode === 'form'" class="issue-stack">
        <article v-for="dimension in rubric.dimensions" :key="dimension.id" class="detail-list-card">
          <h4>{{ dimension.name }} · {{ dimension.maxScore }} 分</h4>
          <ul>
            <li>评分说明：{{ dimension.description }}</li>
            <li>扣分规则：{{ deductionText(dimension.name) }}</li>
            <li>门禁/风险：{{ gateText(dimension.name) }}</li>
            <li>评语要求：{{ commentText(dimension.name) }}</li>
          </ul>
        </article>
      </div>
      <pre v-else class="yaml-preview">{{ rubric.yaml }}</pre>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>来源与版本</h3>
          <p class="panel__description">帮助老师区分正式标准与副本草稿，避免误用未确认版本。</p>
        </div>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>创建方式</span><strong>{{ sourceLabel(rubric.source) }}</strong></div>
        <div class="summary-item"><span>创建时间</span><strong>{{ rubric.createdAt ?? rubric.updatedAt }}</strong></div>
        <div class="summary-item"><span>最近编辑</span><strong>{{ rubric.updatedAt }}</strong></div>
        <div class="summary-item"><span>编辑次数</span><strong>{{ rubric.editCount ?? 0 }} 次</strong></div>
        <div v-if="rubric.copiedFromName" class="summary-item"><span>原始标准</span><strong>{{ rubric.copiedFromName }}</strong></div>
        <div class="summary-item"><span>当前状态</span><strong>{{ statusLabel(rubric.status) }}</strong></div>
      </div>
    </section>
  </section>

  <section v-else class="view">
    <section class="panel">
      <div class="empty-state">未找到对应的评分标准，请返回标准库重新选择。</div>
      <div class="toolbar__actions">
        <RouterLink :to="{ name: 'task-rubrics', params: { taskId: route.params.taskId } }" class="action-button action-button--ghost">
          返回评分标准
        </RouterLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const route = useRoute();
const router = useRouter();
const taskStore = useTaskContextStore();
const configStore = useConfigStore();

const viewMode = ref<"form" | "yaml">("form");
const keyRulesOnly = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const rubric = computed(() => configStore.rubrics.find((item) => item.id === String(route.params.rubricId)) ?? null);

const statusLabel = (status: string) => {
  const map: Record<string, string> = { draft: "草稿", confirmed: "已确认", in_use: "使用中" };
  return map[status] ?? status;
};

const sourceLabel = (source: string) => {
  const map: Record<string, string> = {
    manual: "手工创建",
    template_copy: "模板复制",
    text_generated: "文本生成",
    rubric_copy: "已有标准副本",
  };
  return map[source] ?? source;
};

const matchLabelMap = {
  fit: "适合当前任务",
  adjust: "建议调整后使用",
  avoid: "不建议直接使用",
} as const;

const matchClassMap = {
  fit: "pill--good",
  adjust: "pill--warn",
  avoid: "pill--warn",
} as const;

const matchLevel = computed(() => {
  if (!rubric.value || !taskStore.currentTask) return "adjust";
  const taskLabel = `${taskStore.currentTask.taskType} ${taskStore.currentTask.taskName}`.toLowerCase();
  const rubricLabel = `${rubric.value.name} ${rubric.value.description}`.toLowerCase();
  if (rubric.value.warnings.length >= 2) return "avoid";
  if (taskLabel.includes("考试") && !rubricLabel.includes("考试")) return "adjust";
  if (taskLabel.includes("文档") && rubricLabel.includes("通用") && rubric.value.warnings.length > 0) return "adjust";
  return "fit";
});

const canDeleteCopy = computed(
  () => Boolean(rubric.value && rubric.value.source === "rubric_copy" && rubric.value.status === "draft" && rubric.value.id !== configStore.currentRubric?.id),
);

const qualityFindings = computed(() => {
  if (!rubric.value || !taskStore.currentTask) return [];
  const findings = [...rubric.value.warnings];
  if (rubric.value.totalScore !== taskStore.currentTask.score) {
    findings.push(`总分 ${rubric.value.totalScore} 与当前任务满分 ${taskStore.currentTask.score} 不一致。`);
  }
  if (matchLevel.value === "adjust") {
    findings.push("该标准与当前任务基本适配，但建议先核对任务类型和评分重点后再使用。");
  }
  if (matchLevel.value === "avoid") {
    findings.push("当前风险提示较多，不建议直接绑定到当前任务。");
  }
  return [...new Set(findings)];
});

const deductionText = (dimensionName: string) => {
  if (rubric.value?.warnings.length) {
    return `请重点核对与“${dimensionName}”相关的扣分规则；当前版本未把扣分点单独结构化，建议同时查看 YAML 视图。`;
  }
  return `当前版本未单独拆分“${dimensionName}”的扣分规则，建议以评分说明和 YAML 原文为准。`;
};

const gateText = (dimensionName: string) => {
  if (rubric.value?.warnings.some((item) => item.includes("门禁"))) {
    return `“${dimensionName}”所在标准存在门禁类提醒，绑定前建议确认是否需要补充通过/阻断规则。`;
  }
  return `当前未发现“${dimensionName}”对应的门禁缺失提示，可按现有规则执行。`;
};

const commentText = (dimensionName: string) => {
  return `建议评语明确说明“${dimensionName}”的得分依据、主要缺失点以及下一步改进方向。`;
};

const bindRubric = async () => {
  if (!rubric.value || !taskStore.currentTask) return;
  const confirmed = window.confirm(
    `将“${rubric.value.name} ${rubric.value.version}”绑定到当前任务？\n\n当前任务：${taskStore.currentTask.taskName}\n匹配判断：${matchLabelMap[matchLevel.value]}`,
  );
  if (!confirmed) return;
  await configStore.bindRubric(taskStore.currentTask.id, rubric.value.id);
};

const deleteCopy = async () => {
  if (!rubric.value) return;
  const confirmed = window.confirm(
    `删除评分标准副本\n\n名称：${rubric.value.name}\n版本：${rubric.value.version}\n状态：草稿\n删除后不可恢复。`,
  );
  if (!confirmed) return;
  await configStore.deleteRubricCopy(rubric.value.id);
  await router.replace({ name: "task-rubrics", params: { taskId: taskStore.currentTask?.id } });
};
</script>
