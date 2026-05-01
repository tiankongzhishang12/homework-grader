<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">标准答案</div>
        <h2 class="hero-card__title">上传后先解析，再手动激活为当前版本</h2>
        <p class="hero-card__text">
          标准答案是任务配置中的正式对象。新文件上传后先进入解析流程，只有老师手动激活后才会替换当前使用版本。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill">{{ currentAnswer ? currentAnswer.version : "暂无版本" }}</span>
        <span class="pill" :class="currentAnswer ? parseStatusTone(currentAnswer.parseStatus) : 'pill--warn'">
          {{ currentAnswer ? parseStatusLabel(currentAnswer.parseStatus) : "待上传" }}
        </span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>当前生效版本</h3>
            <p class="panel__description">正在被当前任务使用的标准答案版本。</p>
          </div>
          <button class="action-button" :disabled="configStore.saving" @click="triggerUpload">
            {{ configStore.saving ? "处理中..." : "上传标准答案" }}
          </button>
          <input ref="fileInput" class="hidden-input" type="file" accept=".doc,.docx,.pdf" @change="onFileChange" />
        </div>

        <div v-if="currentAnswer" class="config-summary-stack">
          <article class="detail-block detail-block--highlight">
            <h4>{{ currentAnswer.fileName }}</h4>
            <p>{{ currentAnswer.version }} · 上传于 {{ currentAnswer.uploadedAt }}</p>
          </article>

          <div class="summary-grid">
            <div class="summary-item">
              <span>解析状态</span>
              <strong>{{ parseStatusLabel(currentAnswer.parseStatus) }}</strong>
            </div>
            <div class="summary-item">
              <span>配置状态</span>
              <strong>{{ configStatusLabel(currentAnswer.status) }}</strong>
            </div>
            <div class="summary-item">
              <span>条目数</span>
              <strong>{{ currentAnswer.itemCount }}</strong>
            </div>
            <div class="summary-item">
              <span>最近激活</span>
              <strong>{{ currentAnswer.activatedAt ?? "尚未激活" }}</strong>
            </div>
          </div>

          <div v-if="currentAnswer.parseMessage" class="inline-alert inline-alert--warn">
            {{ currentAnswer.parseMessage }}
          </div>
        </div>

        <div v-else class="empty-state">当前任务尚未上传任何标准答案版本。</div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>操作规则</h3>
        </div>
        <ul class="detail-list">
          <li>支持上传 `.doc`、`.docx`、`.pdf` 标准答案文件。</li>
          <li>新文件默认进入解析流程，不会自动覆盖当前版本。</li>
          <li>解析失败的版本不能直接激活，需要重新上传或修复后再试。</li>
        </ul>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>版本历史</h3>
          <p class="panel__description">查看历史版本并决定是否切换为当前使用版本。</p>
        </div>
        <button class="action-button action-button--ghost" :disabled="refreshing" @click="reloadAnswers">
          {{ refreshing ? "刷新中..." : "刷新版本列表" }}
        </button>
      </div>

      <div v-if="configStore.answers.length > 0" class="config-card-stack">
        <article v-for="item in configStore.answers" :key="item.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">{{ item.fileName }}</div>
              <div class="rubric-card__meta">{{ item.version }} · 上传于 {{ item.uploadedAt }}</div>
            </div>
            <div class="tag-row">
              <span class="status-badge" :class="parseStatusTone(item.parseStatus)">{{ parseStatusLabel(item.parseStatus) }}</span>
              <span class="status-badge" :class="configStatusTone(item.status)">{{ configStatusLabel(item.status) }}</span>
              <span v-if="item.current" class="tag tag--good">当前版本</span>
            </div>
          </div>

          <div class="summary-grid">
            <div class="summary-item">
              <span>条目数</span>
              <strong>{{ item.itemCount }}</strong>
            </div>
            <div class="summary-item">
              <span>最近激活</span>
              <strong>{{ item.activatedAt ?? "尚未激活" }}</strong>
            </div>
          </div>

          <div v-if="item.parseMessage" class="inline-alert inline-alert--risk">
            {{ item.parseMessage }}
          </div>

          <div class="toolbar__actions">
            <button
              class="action-button"
              :disabled="item.current || item.status === 'parse_failed' || configStore.saving"
              @click="activate(item.id)"
            >
              {{ item.current ? "当前使用中" : "设为当前版本" }}
            </button>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">暂无历史版本。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const fileInput = ref<HTMLInputElement | null>(null);
const refreshing = ref(false);

watch(
  () => taskStore.currentTask?.id,
  async (taskId) => {
    if (taskId) {
      await configStore.loadTaskConfig(taskId);
    }
  },
  { immediate: true },
);

const currentAnswer = computed(() => configStore.answers.find((item) => item.current) ?? configStore.answers[0] ?? null);

const parseStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    uploading: "上传中",
    parsing: "解析中",
    parse_failed: "解析失败",
    draft: "已解析（草稿）",
    confirmed: "已确认",
    in_use: "使用中",
  };
  return map[status] ?? status;
};

const configStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: "草稿",
    confirmed: "已确认",
    in_use: "使用中",
    parse_failed: "解析失败",
  };
  return map[status] ?? status;
};

const parseStatusTone = (status: string) => {
  if (status === "in_use" || status === "confirmed") return "status-badge--good";
  if (status === "parse_failed") return "status-badge--risk";
  return "status-badge--warn";
};

const configStatusTone = (status: string) => {
  if (status === "in_use" || status === "confirmed") return "status-badge--good";
  if (status === "parse_failed") return "status-badge--risk";
  return "status-badge--warn";
};

const triggerUpload = () => fileInput.value?.click();

const onFileChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file || !taskStore.currentTask) return;
  await configStore.uploadAnswer(taskStore.currentTask.id, file);
  (event.target as HTMLInputElement).value = "";
};

const activate = async (versionId: string) => {
  if (!taskStore.currentTask) return;
  await configStore.activateAnswer(taskStore.currentTask.id, versionId);
};

const reloadAnswers = async () => {
  if (!taskStore.currentTask) return;
  refreshing.value = true;
  try {
    await configStore.loadTaskConfig(taskStore.currentTask.id);
  } finally {
    refreshing.value = false;
  }
};
</script>
