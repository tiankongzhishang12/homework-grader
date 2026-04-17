<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card">
      <div>
        <div class="eyebrow">评分标准配置</div>
        <h2 class="hero-card__title">优先从标准库选择，也支持从文本生成 Rubric 初稿</h2>
        <p class="hero-card__text">
          首发版采用“表单编辑 + YAML 预览”的方式维护评分标准。老师可以直接绑定已有版本，也可以从自然语言生成新的 Rubric 草稿后再保存。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill pill--good">当前绑定：{{ configStore.currentRubric?.version ?? "未绑定" }}</span>
        <RouterLink :to="{ name: 'task-rubric-generator', params: { taskId: taskStore.currentTask.id } }" class="action-button action-button--ghost">
          文本生成 Rubric
        </RouterLink>
      </div>
    </div>

    <section class="panel">
      <div class="panel__header">
        <h3>评分标准库</h3>
      </div>
      <div class="issue-stack">
        <article v-for="item in configStore.rubrics" :key="item.id" class="rubric-card">
          <div class="rubric-card__top">
            <div>
              <div class="rubric-card__title">{{ item.name }}</div>
              <div class="rubric-card__meta">{{ item.version }} · {{ sourceLabel(item.source) }} · {{ item.updatedAt }}</div>
            </div>
            <span class="status-badge" :class="item.status === 'in_use' || item.status === 'confirmed' ? 'status-badge--good' : 'status-badge--warn'">
              {{ statusLabel(item.status) }}
            </span>
          </div>
          <p class="rubric-card__summary">{{ item.description }}</p>
          <div class="tag-row">
            <span class="tag">{{ item.totalScore }} 分</span>
            <span class="tag">{{ item.dimensions.length }} 个维度</span>
          </div>
          <article class="detail-list-card">
            <h4>维度预览</h4>
            <ul>
              <li v-for="dimension in item.dimensions" :key="dimension.id">{{ dimension.name }} · {{ dimension.maxScore }} 分</li>
            </ul>
          </article>
          <pre class="yaml-preview yaml-preview--compact">{{ item.yaml }}</pre>
          <div v-if="item.warnings.length > 0" class="inline-alert inline-alert--warn">
            {{ item.warnings.join("；") }}
          </div>
          <div class="toolbar__actions">
            <button
              class="action-button"
              :disabled="configStore.saving || item.id === configStore.currentRubric?.id || item.status === 'draft'"
              @click="bind(item.id)"
            >
              {{ item.id === configStore.currentRubric?.id ? "当前已绑定" : "绑定当前任务" }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { RouterLink } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();

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
  const map: Record<string, string> = { draft: "草稿", confirmed: "已确认", in_use: "使用中" };
  return map[status] ?? status;
};

const sourceLabel = (source: string) => {
  const map: Record<string, string> = { manual: "手工创建", template_copy: "模板复制", text_generated: "文本生成" };
  return map[source] ?? source;
};

const bind = async (rubricId: string) => {
  if (!taskStore.currentTask) return;
  await configStore.bindRubric(taskStore.currentTask.id, rubricId);
};
</script>
