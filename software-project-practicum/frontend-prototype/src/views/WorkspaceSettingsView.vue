<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">学生提交</div>
        <h2 class="hero-card__title">学生作业管理</h2>
        <p class="hero-card__text">
          上传、查看并管理当前任务的学生提交文件。新上传或重新上传的作业会在“批改新增/更新提交”时自动进入本次阅卷。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill">{{ taskStore.currentTask.taskName }}</span>
        <span class="pill" :class="pendingCount > 0 ? 'pill--warn' : 'pill--good'">
          {{ pendingCount > 0 ? `${pendingCount} 份待批改` : "暂无待批改" }}
        </span>
      </div>
    </div>

    <section class="submission-summary-grid">
      <article class="metric-card">
        <span>应交学生</span>
        <strong>{{ summary.studentCount }}</strong>
      </article>
      <article class="metric-card">
        <span>已上传</span>
        <strong>{{ summary.submittedCount }}</strong>
      </article>
      <article class="metric-card">
        <span>待批改</span>
        <strong>{{ summary.pendingGradingCount }}</strong>
      </article>
      <article class="metric-card">
        <span>已评分</span>
        <strong>{{ summary.gradedCount }}</strong>
      </article>
      <article class="metric-card">
        <span>异常</span>
        <strong>{{ summary.failedCount }}</strong>
      </article>
    </section>

    <div class="submission-management-grid">
      <section class="panel submission-upload-card">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>上传学生作业</h3>
            <p class="panel__description">支持 .doc / .docx / .pdf。上传后会作为增量阅卷的待处理提交。</p>
          </div>
          <button class="action-button action-button--ghost" :disabled="configStore.saving" @click="checkWorkspace">
            检测工作区
          </button>
        </div>

        <div class="config-form-grid">
          <label class="field">
            <span>学生 ID / 学号</span>
            <input v-model="studentId" class="field__input" type="text" placeholder="请输入学生 ID 或学号" />
            <small class="field__hint">当前版本需要输入系统中的学生 ID，后续将支持学生选择器和按学号匹配。</small>
          </label>
          <label class="field">
            <span>作业文件</span>
            <input class="field__input" type="file" accept=".doc,.docx,.pdf" @change="onFileChange" />
            <small class="field__hint">支持格式：{{ supportedFormats }}</small>
          </label>
        </div>

        <div class="submission-upload-actions">
          <button class="action-button" :disabled="configStore.saving || !taskStore.currentTask.assessmentId || !selectedFile" @click="uploadSubmission">
            {{ configStore.saving ? "上传中..." : "上传作业" }}
          </button>
        </div>

        <div v-if="configStore.lastUploadResult" class="submission-upload-result">
          <strong>上传成功</strong>
          <span>文件：{{ configStore.lastUploadResult.file ?? selectedFile?.name ?? "-" }}</span>
          <span>状态：已保存，开始阅卷时将自动处理。</span>
          <details v-if="configStore.lastUploadResult.rawWorkspace" class="workspace-debug-details">
            <summary>上传技术信息</summary>
            <dl>
              <div>
                <dt>rawWorkspace synced</dt>
                <dd>{{ configStore.lastUploadResult.rawWorkspace.synced ? "true" : "false" }}</dd>
              </div>
              <div>
                <dt>path</dt>
                <dd>{{ configStore.lastUploadResult.rawWorkspace.path ?? "-" }}</dd>
              </div>
              <div>
                <dt>message</dt>
                <dd>{{ configStore.lastUploadResult.rawWorkspace.message ?? "-" }}</dd>
              </div>
            </dl>
          </details>
        </div>

        <div v-if="pendingCount > 0" class="inline-alert inline-alert--warn">
          已有 {{ pendingCount }} 份作业待批改。可前往“批量阅卷”页面点击“批改新增/更新提交”。
          <RouterLink :to="{ name: 'task-grading', params: { taskId: taskStore.currentTask.id } }">前往批量阅卷</RouterLink>
        </div>
      </section>

      <aside class="panel submission-status-card">
        <div class="panel__header">
          <h3>提交摘要</h3>
        </div>
        <div class="config-card-stack">
          <article class="config-record-card">
            <div class="submission-status-row"><span>已上传</span><strong>{{ summary.submittedCount }}</strong></div>
            <div class="submission-status-row"><span>待批改</span><strong>{{ summary.pendingGradingCount }}</strong></div>
            <div class="submission-status-row"><span>已评分</span><strong>{{ summary.gradedCount }}</strong></div>
            <div class="submission-status-row"><span>异常</span><strong>{{ summary.failedCount }}</strong></div>
            <div class="submission-status-row"><span>支持格式</span><strong>{{ supportedFormats }}</strong></div>
          </article>
        </div>

        <details class="workspace-debug-details">
          <summary>工作区路径 / 开发调试信息</summary>
          <dl>
            <div>
              <dt>assessmentId</dt>
              <dd>{{ taskStore.currentTask.assessmentId ?? "-" }}</dd>
            </div>
            <div v-for="item in workspaceEntries" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </div>
            <div>
              <dt>upload API</dt>
              <dd>POST /api/assessments/{assessmentId}/submissions/upload</dd>
            </div>
            <div>
              <dt>list API</dt>
              <dd>GET /api/assessments/{assessmentId}/submissions</dd>
            </div>
          </dl>
        </details>
      </aside>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3>学生提交记录</h3>
          <p class="panel__description">展示当前任务下已上传的学生作业及评分状态。</p>
        </div>
      </div>

      <div v-if="configStore.submissions.length > 0" class="submission-record-list">
        <article v-for="item in configStore.submissions" :key="item.id" class="submission-record-card">
          <div>
            <div class="submission-record-card__title">
              {{ studentTitle(item) }}
            </div>
            <div class="submission-record-card__meta">
              文件：{{ item.file_name ?? item.source_submission_id ?? "-" }} ·
              提交时间：{{ formatDate(item.submitted_at) }} ·
              第 {{ item.attempt_no ?? 1 }} 次提交
            </div>
            <div class="submission-record-card__meta">
              <span class="submission-status-badge">{{ uploadStatusLabel(item.submit_status) }}</span>
              <span class="submission-status-badge" :class="`submission-status-badge--${gradingStatusClass(item.grading_status)}`">
                {{ gradingStatusLabel(item.grading_status) }}
              </span>
              <span v-if="item.final_score !== undefined && item.final_score !== null" class="submission-status-badge submission-status-badge--score">
                {{ item.final_score }} 分
              </span>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">当前任务还没有学生作业，请先上传。</div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";
import type { SubmissionRecord } from "../types";

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

const emptySummary = {
  studentCount: 0,
  submittedCount: 0,
  validSubmissionCount: 0,
  pendingGradingCount: 0,
  gradedCount: 0,
  failedCount: 0,
  supportedExtensions: ["doc", "docx", "pdf"],
};

const summary = computed(() => configStore.submissionSummary ?? emptySummary);
const pendingCount = computed(() => summary.value.pendingGradingCount ?? 0);
const supportedFormats = computed(() => (summary.value.supportedExtensions?.length ? summary.value.supportedExtensions : ["doc", "docx", "pdf"]).join(" / "));

const workspaceEntries = computed(() => {
  if (!configStore.workspace) return [];
  return [
    { label: "workspace root", value: configStore.workspace.rootPath },
    { label: "raw", value: configStore.workspace.rawPath },
    { label: "ir", value: configStore.workspace.irPath },
    { label: "scores", value: configStore.workspace.scoresPath },
    { label: "reports", value: configStore.workspace.reportsPath },
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

const formatDate = (value?: string) => {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
};

const studentTitle = (item: SubmissionRecord) => {
  const name = item.student_name?.trim() || `studentId ${item.student_id ?? "-"}`;
  const no = item.student_no?.trim() || `提交 #${item.id}`;
  return `${name}（${no}）`;
};

const uploadStatusLabel = (status?: string) => {
  const map: Record<string, string> = {
    UPLOADED: "已上传",
    SUBMITTED: "已提交",
    FAILED: "提交异常",
  };
  return map[status ?? ""] ?? status ?? "已保存";
};

const gradingStatusLabel = (status?: string) => {
  const map: Record<string, string> = {
    PENDING: "待批改",
    GRADED: "已评分",
    FAILED: "评分失败",
  };
  return map[status ?? ""] ?? status ?? "待批改";
};

const gradingStatusClass = (status?: string) => {
  if (status === "GRADED") return "graded";
  if (status === "FAILED") return "failed";
  return "pending";
};
</script>
