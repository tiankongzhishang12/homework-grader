<template>
  <section class="view" v-if="taskStore.currentTask && configStore.workspace">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">工作区路径</div>
        <h2 class="hero-card__title">先检测目录可用性，再解除阅卷阻断</h2>
        <p class="hero-card__text">
          工作区路径直接影响批量阅卷能否启动。这里不仅展示目录结构，还要支持检测、初始化和重新检测。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="configStore.workspace.status === 'valid' ? 'pill--good' : 'pill--warn'">{{ workspaceStatusLabel }}</span>
        <span class="pill">{{ configStore.workspace.lastCheckedAt ?? "尚未检测" }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>路径状态</h3>
            <p class="panel__description">只有检测通过后，任务配置页中的“开始阅卷”按钮才会解除阻断。</p>
          </div>
          <div class="toolbar__actions">
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="checkWorkspace">检测路径</button>
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="initWorkspace">初始化目录</button>
            <button class="action-button" :disabled="configStore.saving" @click="checkWorkspace">重新检测</button>
          </div>
        </div>

        <div class="config-card-stack">
          <article class="config-record-card" v-for="item in workspaceEntries" :key="item.label">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">{{ item.label }}</div>
                <div class="rubric-card__meta">{{ item.hint }}</div>
              </div>
            </div>
            <p class="path-code">{{ item.value }}</p>
          </article>
        </div>

        <div class="inline-alert" :class="configStore.workspace.status === 'valid' ? 'inline-alert--good' : 'inline-alert--warn'">
          {{ configStore.workspace.lastMessage ?? "尚未检测路径。" }}
        </div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>当前建议</h3>
        </div>
        <div class="detail-block detail-block--highlight">
          <h4>{{ workspaceStatusLabel }}</h4>
          <p>{{ nextWorkspaceAction }}</p>
        </div>
      </aside>
    </div>
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
  const map: Record<string, string> = {
    unchecked: "未检测",
    valid: "检测通过",
    invalid: "检测失败",
    initializing: "初始化中",
  };
  return map[configStore.workspace?.status ?? "unchecked"];
});

const workspaceEntries = computed(() => {
  if (!configStore.workspace) return [];
  return [
    { label: "工作区根路径", value: configStore.workspace.rootPath, hint: "任务工作区根目录" },
    { label: "raw", value: configStore.workspace.rawPath, hint: "原始提交文件目录" },
    { label: "ir", value: configStore.workspace.irPath, hint: "预处理后的中间结果目录" },
    { label: "scores", value: configStore.workspace.scoresPath, hint: "评分结果目录" },
    { label: "reports", value: configStore.workspace.reportsPath, hint: "报告与导出目录" },
  ];
});

const nextWorkspaceAction = computed(() => {
  const status = configStore.workspace?.status ?? "unchecked";
  if (status === "valid") return "路径已经满足当前任务的执行条件，可以返回任务配置页继续检查其他步骤。";
  if (status === "initializing") return "目录正在初始化，建议稍后重新检测并确认每个目录都存在。";
  if (status === "invalid") return "请先根据提示修复目录问题，再重新执行检测。";
  return "建议先点击“检测路径”，确认所有目录可用后再开始阅卷。";
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
