<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">评分标准</div>
        <h2 class="hero-card__title">先选合适的 Rubric，再决定直接绑定还是生成副本</h2>
        <p class="hero-card__text">
          候选标准会按适配度、结构完整性和当前任务上下文进行展示。老师先挑选标准，再决定直接绑定，还是基于它生成新副本。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ configStore.currentRubric?.name ?? "未绑定评分标准" }}</span>
        <RouterLink :to="{ name: 'task-rubric-generator', params: { taskId: taskStore.currentTask.id } }" class="action-button action-button--ghost">
          文本生成 Rubric
        </RouterLink>
      </div>
    </div>

    <section class="panel panel--compact">
      <div class="filter-toolbar">
        <input v-model="keyword" class="field__input field__input--search" type="text" placeholder="搜索评分标准名称" />
        <div class="select-mock">
          <span class="select-mock__label">状态</span>
          <select v-model="statusFilter" class="selector-select">
            <option value="all">全部</option>
            <option value="draft">草稿</option>
            <option value="confirmed">已确认</option>
            <option value="in_use">使用中</option>
          </select>
        </div>
        <div class="select-mock">
          <span class="select-mock__label">来源</span>
          <select v-model="sourceFilter" class="selector-select">
            <option value="all">全部</option>
            <option value="manual">手工创建</option>
            <option value="template_copy">模板复制</option>
            <option value="text_generated">文本生成</option>
            <option value="rubric_copy">标准副本</option>
          </select>
        </div>
        <div class="select-mock">
          <span class="select-mock__label">适配度</span>
          <select v-model="matchFilter" class="selector-select">
            <option value="all">全部</option>
            <option value="fit">适合当前任务</option>
            <option value="adjust">建议调整后使用</option>
            <option value="avoid">不建议直接使用</option>
          </select>
        </div>
      </div>
    </section>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>候选评分标准</h3>
            <p class="panel__description">优先查看适配当前任务的标准，草稿副本允许删除，正式标准只支持查看和绑定。</p>
          </div>
          <span class="pill">{{ filteredRubrics.length }} 个候选项</span>
        </div>

        <div v-if="filteredRubrics.length > 0" class="config-card-stack">
          <article v-for="item in filteredRubrics" :key="item.id" class="config-record-card">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">{{ item.name }}</div>
                <div class="rubric-card__meta">{{ item.version }} · {{ sourceLabel(item.source) }} · {{ item.updatedAt }}</div>
              </div>
              <div class="tag-row">
                <span class="status-badge" :class="item.status === 'draft' ? 'status-badge--warn' : 'status-badge--good'">
                  {{ statusLabel(item.status) }}
                </span>
                <span class="pill" :class="matchClassMap[matchLevel(item)]">{{ matchLabelMap[matchLevel(item)] }}</span>
                <span v-if="item.id === configStore.currentRubric?.id" class="tag tag--good">当前绑定</span>
              </div>
            </div>

            <p class="rubric-card__summary">{{ item.description }}</p>

            <div class="summary-grid">
              <div class="summary-item">
                <span>总分</span>
                <strong>{{ item.totalScore }}</strong>
              </div>
              <div class="summary-item">
                <span>维度数</span>
                <strong>{{ item.dimensions.length }}</strong>
              </div>
              <div class="summary-item">
                <span>风险提示</span>
                <strong>{{ item.warnings.length }}</strong>
              </div>
              <div class="summary-item">
                <span>最近使用</span>
                <strong>{{ item.lastUsedTaskName ?? "暂无记录" }}</strong>
              </div>
            </div>

            <div v-if="item.warnings.length > 0" class="inline-alert inline-alert--warn">
              {{ item.warnings.join("；") }}
            </div>

            <div class="toolbar__actions">
              <RouterLink :to="{ name: 'task-rubric-detail', params: { taskId: taskStore.currentTask.id, rubricId: item.id } }" class="action-button action-button--ghost">
                查看详情
              </RouterLink>
              <RouterLink
                :to="{ name: 'task-rubric-generator', params: { taskId: taskStore.currentTask.id }, query: { baseRubricId: item.id } }"
                class="action-button action-button--ghost"
              >
                生成副本
              </RouterLink>
              <button
                v-if="canDeleteCopy(item)"
                class="action-button action-button--ghost"
                :disabled="configStore.saving"
                @click="deleteCopy(item)"
              >
                删除副本
              </button>
              <button
                class="action-button"
                :disabled="configStore.saving || item.id === configStore.currentRubric?.id"
                @click="bind(item.id)"
              >
                {{ item.id === configStore.currentRubric?.id ? "当前已绑定" : "绑定到当前任务" }}
              </button>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">没有符合当前筛选条件的评分标准。</div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>当前绑定</h3>
        </div>
        <div v-if="configStore.currentRubric" class="config-summary-stack">
          <article class="detail-block detail-block--highlight">
            <h4>{{ configStore.currentRubric.name }}</h4>
            <p>{{ configStore.currentRubric.version }} · {{ sourceLabel(configStore.currentRubric.source) }}</p>
          </article>
          <div class="summary-grid">
            <div class="summary-item">
              <span>总分</span>
              <strong>{{ configStore.currentRubric.totalScore }}</strong>
            </div>
            <div class="summary-item">
              <span>维度数</span>
              <strong>{{ configStore.currentRubric.dimensions.length }}</strong>
            </div>
          </div>
        </div>
        <div v-else class="empty-state empty-state--small">当前任务尚未绑定 Rubric。</div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import type { Rubric } from "../types";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();

const keyword = ref("");
const statusFilter = ref<"all" | "draft" | "confirmed" | "in_use">("all");
const sourceFilter = ref<"all" | "manual" | "template_copy" | "text_generated" | "rubric_copy">("all");
const matchFilter = ref<"all" | "fit" | "adjust" | "avoid">("all");

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: "草稿",
    confirmed: "已确认",
    in_use: "使用中",
  };
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

const matchLevel = (rubric: Rubric) => {
  if (!taskStore.currentTask) return "adjust";
  const taskLabel = `${taskStore.currentTask.taskType} ${taskStore.currentTask.taskName}`.toLowerCase();
  const rubricLabel = `${rubric.name} ${rubric.description}`.toLowerCase();
  if (taskLabel.includes("考试") && !rubricLabel.includes("考试")) return "adjust";
  if (taskLabel.includes("文档") && rubricLabel.includes("通用") && rubric.warnings.length > 0) return "adjust";
  if (rubric.warnings.length >= 2) return "avoid";
  return "fit";
};

const canDeleteCopy = (rubric: Rubric) =>
  rubric.source === "rubric_copy" && rubric.status === "draft" && rubric.id !== configStore.currentRubric?.id;

const filteredRubrics = computed(() => {
  const search = keyword.value.trim().toLowerCase();
  return configStore.rubrics.filter((item) => {
    const matchesKeyword = !search || item.name.toLowerCase().includes(search);
    const matchesStatus = statusFilter.value === "all" || item.status === statusFilter.value;
    const matchesSource = sourceFilter.value === "all" || item.source === sourceFilter.value;
    const matchesLevel = matchFilter.value === "all" || matchLevel(item) === matchFilter.value;
    return matchesKeyword && matchesStatus && matchesSource && matchesLevel;
  });
});

const bind = async (rubricId: string) => {
  if (!taskStore.currentTask) return;
  const target = configStore.rubrics.find((item) => item.id === rubricId);
  if (!target) return;
  const confirmed = window.confirm(
    `将 “${target.name} ${target.version}” 绑定到当前任务？\n\n当前任务：${taskStore.currentTask.taskName}\n风险提示：${target.warnings.length} 条`,
  );
  if (!confirmed) return;
  await configStore.bindRubric(taskStore.currentTask.id, rubricId);
};

const deleteCopy = async (rubric: Rubric) => {
  const confirmed = window.confirm(
    `删除评分标准副本\n\n名称：${rubric.name}\n版本：${rubric.version}\n状态：草稿\n删除后不可恢复。`,
  );
  if (!confirmed) return;
  await configStore.deleteRubricCopy(rubric.id);
};
</script>
