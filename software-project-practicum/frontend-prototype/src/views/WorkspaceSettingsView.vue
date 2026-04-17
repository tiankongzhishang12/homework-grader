<template>
  <section class="view" v-if="taskStore.currentTask && configStore.workspace">
    <div class="hero-card">
      <div>
        <div class="eyebrow">批量阅卷路径配置</div>
        <h2 class="hero-card__title">路径配置是可操作模块，检测失败会直接阻断开始阅卷</h2>
        <p class="hero-card__text">
          当前任务工作区由系统按规则生成。页面不仅展示路径，还要支持检测、初始化和重新检测，让老师明确知道当前目录是否满足阅卷执行条件。
        </p>
      </div>
      <div class="hero-card__meta">
        <span class="pill" :class="configStore.workspace.status === 'valid' ? 'pill--good' : 'pill--warn'">{{ workspaceStatusLabel }}</span>
        <span class="pill">{{ configStore.workspace.lastCheckedAt ?? "尚未检测" }}</span>
      </div>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>工作区路径</h3>
          <p class="panel__description">只有路径检测通过后，任务配置页中的“开始阅卷”按钮才会解除阻断。</p>
        </div>
        <div class="toolbar__actions">
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="checkWorkspace">检测路径</button>
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initWorkspace">初始化目录</button>
          <button class="action-button" :disabled="configStore.saving" @click="checkWorkspace">重新检测</button>
        </div>
      </div>

      <div class="issue-stack">
        <article class="detail-block">
          <h4>工作区根路径</h4>
          <p class="path-code">{{ configStore.workspace.rootPath }}</p>
        </article>
        <article class="detail-block">
          <h4>raw/</h4>
          <p class="path-code">{{ configStore.workspace.rawPath }}</p>
        </article>
        <article class="detail-block">
          <h4>ir/</h4>
          <p class="path-code">{{ configStore.workspace.irPath }}</p>
        </article>
        <article class="detail-block">
          <h4>scores/</h4>
          <p class="path-code">{{ configStore.workspace.scoresPath }}</p>
        </article>
        <article class="detail-block">
          <h4>reports/</h4>
          <p class="path-code">{{ configStore.workspace.reportsPath }}</p>
        </article>
      </div>

      <div class="inline-alert" :class="configStore.workspace.status === 'valid' ? 'inline-alert--good' : 'inline-alert--warn'">
        {{ configStore.workspace.lastMessage ?? "尚未检测路径。" }}
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
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

const workspaceStatusLabel = computed(() => {
  const map: Record<string, string> = { unchecked: "未检测", valid: "检测通过", invalid: "检测失败", initializing: "初始化中" };
  return map[configStore.workspace?.status ?? "unchecked"];
});

const checkWorkspace = async () => {
  if (!taskStore.currentTask) return;
  await configStore.checkWorkspace(taskStore.currentTask.id);
};

const initWorkspace = async () => {
  if (!taskStore.currentTask) return;
  await configStore.initWorkspace(taskStore.currentTask.id);
};
</script>
