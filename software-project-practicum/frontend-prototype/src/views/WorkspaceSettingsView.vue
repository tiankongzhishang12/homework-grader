<template>
  <section class="view" v-if="taskStore.currentTask && configStore.workspace">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">学生作业与工作区</div>
        <h2 class="hero-card__title">先确认工作区，再做单学生单文件上传</h2>
        <p class="hero-card__text">
          第一版只支持单学生单文件上传。上传成功后会显示 `rawWorkspace.synced`、`path` 和 `message`，方便确认 Python raw 工作区是否已接收到文件。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="configStore.workspace.status === 'valid' ? 'pill--good' : 'pill--warn'">
          {{ workspaceStatusLabel }}
        </span>
        <span class="pill">{{ taskStore.currentTask.assessmentId ?? "缺少 assessmentId" }}</span>
      </div>
    </div>

    <div class="config-subpage-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>上传学生作业</h3>
            <p class="panel__description">真实接口：`POST /api/assessments/{assessmentId}/submissions/upload?studentId=...`</p>
          </div>
          <div class="toolbar__actions">
            <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="checkWorkspace">检测路径</button>
            <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.assessmentId || !selectedFile" @click="uploadSubmission">
              {{ configStore.saving ? "上传中..." : "上传作业" }}
            </button>
          </div>
        </div>

        <div class="config-form-grid">
          <label class="field">
            <span>studentId</span>
            <input v-model="studentId" class="field__input" type="text" placeholder="请输入真实 studentId" />
          </label>
          <label class="field">
            <span>作业文件</span>
            <input class="field__input" type="file" accept=".doc,.docx,.pdf" @change="onFileChange" />
          </label>
        </div>

        <div v-if="configStore.lastUploadResult?.rawWorkspace" class="inline-alert" :class="configStore.lastUploadResult.rawWorkspace.synced ? 'inline-alert--good' : 'inline-alert--warn'">
          {{ configStore.summarizeLatestUpload() }}
        </div>
      </section>

      <aside class="panel config-side-panel">
        <div class="panel__header">
          <h3>工作区摘要</h3>
        </div>
        <div class="config-card-stack">
          <article v-for="item in workspaceEntries" :key="item.label" class="config-record-card">
            <div class="config-record-card__top">
              <div>
                <div class="rubric-card__title">{{ item.label }}</div>
                <div class="rubric-card__meta">{{ item.hint }}</div>
              </div>
            </div>
            <p class="path-code">{{ item.value }}</p>
          </article>
        </div>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>当前 assessment 提交记录</h3>
          <p class="panel__description">真实接口：`GET /api/assessments/{assessmentId}/submissions`</p>
        </div>
      </div>
      <div v-if="configStore.submissions.length > 0" class="config-card-stack">
        <article v-for="item in configStore.submissions" :key="item.id" class="config-record-card">
          <div class="config-record-card__top">
            <div>
              <div class="rubric-card__title">Submission #{{ item.id }}</div>
              <div class="rubric-card__meta">studentId {{ item.student_id ?? "-" }} | {{ item.submit_status ?? "-" }}</div>
            </div>
          </div>
          <p class="rubric-card__summary">{{ item.source_submission_id ?? item.submitted_at ?? "已存在提交记录" }}</p>
        </article>
      </div>
      <div v-else class="empty-state">当前 assessment 还没有真实提交记录。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const taskStore = useTaskContextStore();
const configStore = useConfigStore();
const studentId = ref("");
const selectedFile = ref<File | null>(null);

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
    { label: "workspace root", value: configStore.workspace.rootPath, hint: "任务工作区根目录" },
    { label: "raw", value: configStore.workspace.rawPath, hint: "原始学生作业目录" },
    { label: "ir", value: configStore.workspace.irPath, hint: "预处理输出目录" },
    { label: "scores", value: configStore.workspace.scoresPath, hint: "评分结果目录" },
    { label: "reports", value: configStore.workspace.reportsPath, hint: "报表目录" },
  ];
});

const onFileChange = (event: Event) => {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
};

const uploadSubmission = async () => {
  if (!taskStore.currentTask || !selectedFile.value) return;
  await configStore.uploadSubmission(taskStore.currentTask.id, studentId.value, selectedFile.value);
};

const checkWorkspace = async () => {
  if (!taskStore.currentTask) return;
  await configStore.checkWorkspace(taskStore.currentTask.id);
};
</script>
