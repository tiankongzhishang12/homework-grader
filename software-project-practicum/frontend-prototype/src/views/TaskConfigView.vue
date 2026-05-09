<template>
  <section class="view" v-if="taskStore.currentTask">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">任务配置</div>
        <h2 class="hero-card__title">先完成就绪检查，再启动自动阅卷</h2>
        <p class="hero-card__text">
          这个页面只回答一件事：当前任务是否已经满足执行条件。所有配置都整理为步骤卡，老师只需要逐项补齐即可。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill" :class="taskStore.canStartBatch ? 'pill--good' : 'pill--warn'">
          {{ taskStore.canStartBatch ? "可以开始阅卷" : "存在待处理阻断项" }}
        </span>
        <span class="pill">完成度 {{ taskStore.currentTask.configProgress }}%</span>
        <span class="pill pill--good">已提交 {{ taskStore.currentTask.submittedCount }}/{{ taskStore.currentTask.studentCount }}</span>
      </div>
    </div>

    <section class="panel readiness-panel" :class="taskStore.canStartBatch ? 'readiness-panel--ready' : 'readiness-panel--blocked'">
      <div class="readiness-panel__main">
        <span class="eyebrow">执行检查</span>
        <h3>{{ taskStore.canStartBatch ? "任务已就绪，可以开始阅卷" : `当前不能开始阅卷：${pendingSteps.length} 项待处理` }}</h3>
        <p>{{ taskStore.canStartBatch ? "所有关键配置项已经通过检查，建议直接进入批量阅卷。" : nextActionSummary }}</p>
      </div>
      <div class="readiness-panel__actions">
        <RouterLink v-if="pendingSteps[0]" :to="pendingSteps[0].to" class="action-button">
          处理首个阻断项
        </RouterLink>
        <button v-else class="action-button" @click="goToGrading">开始阅卷</button>
      </div>
    </section>

    <section v-if="pendingSteps.length > 0" class="panel priority-checklist">
      <div class="panel__header">
        <div>
          <h3>必须先处理</h3>
          <p class="panel__description">这里只保留会影响自动阅卷启动的事项，每一项都给出直接入口。</p>
        </div>
        <span class="pill pill--warn">{{ pendingSteps.length }} 项</span>
      </div>

      <div class="priority-checklist__list">
        <article v-for="step in pendingSteps" :key="step.id" class="priority-item">
          <div>
            <div class="priority-item__title">{{ step.title }}</div>
            <p>{{ step.summary }}</p>
            <small v-if="step.hint">{{ step.hint }}</small>
          </div>
          <RouterLink :to="step.to" class="action-button action-button--ghost">{{ step.action }}</RouterLink>
        </article>
      </div>
    </section>

    <section v-if="readySteps.length > 0" class="panel compact-complete-panel">
      <div class="panel__header">
        <div>
          <h3>已完成配置</h3>
          <p class="panel__description">已通过的项目保持收起，避免干扰下一步判断。</p>
        </div>
        <span class="pill pill--good">{{ readySteps.length }} 项</span>
      </div>
      <div class="complete-chip-row">
        <span v-for="step in readySteps" :key="step.id" class="tag tag--good">{{ step.title }}</span>
      </div>
    </section>

    <div class="setup-layout setup-layout--legacy">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>就绪检查</h3>
            <p class="panel__description">每张步骤卡只展示状态、当前摘要和下一步动作。</p>
          </div>
          <span class="pill">{{ completedStepCount }}/{{ setupSteps.length }} 已就绪</span>
        </div>

        <div v-if="taskStore.blockers.length > 0" class="inline-alert inline-alert--risk">
          {{ blockerSummary }}
        </div>

        <div class="setup-step-list">
          <article v-for="step in setupSteps" :key="step.id" class="setup-step-card">
            <div class="setup-step-card__index">{{ step.index }}</div>
            <div class="setup-step-card__body">
              <div class="setup-step-card__top">
                <div>
                  <h4>{{ step.title }}</h4>
                  <p class="setup-step-card__description">{{ step.description }}</p>
                </div>
                <span class="status-badge" :class="step.tone">{{ step.status }}</span>
              </div>
              <p class="setup-step-card__summary">{{ step.summary }}</p>
              <div class="setup-step-card__footer">
                <span v-if="step.hint" class="setup-step-card__hint">{{ step.hint }}</span>
                <RouterLink :to="step.to" class="action-button action-button--ghost">{{ step.action }}</RouterLink>
              </div>
            </div>
          </article>
        </div>
      </section>

      <aside class="panel setup-side-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>任务摘要</h3>
            <p class="panel__description">{{ taskStore.currentTask.courseName }} · {{ taskStore.currentTask.className }}</p>
          </div>
          <button class="action-button" :disabled="!taskStore.canStartBatch" @click="goToGrading">开始阅卷</button>
        </div>

        <div class="stats-grid stats-grid--compact">
          <article class="stat-card stat-card--neutral">
            <div class="stat-card__label">学生人数</div>
            <div class="stat-card__value">{{ taskStore.currentTask.studentCount }}</div>
          </article>
          <article class="stat-card stat-card--good">
            <div class="stat-card__label">任务满分</div>
            <div class="stat-card__value">{{ taskStore.currentTask.score }}</div>
          </article>
          <article class="stat-card stat-card--warn">
            <div class="stat-card__label">截止时间</div>
            <div class="stat-card__value stat-card__value--small">{{ taskStore.currentTask.deadline }}</div>
          </article>
        </div>

        <div class="detail-block detail-block--highlight">
          <h4>下一步建议</h4>
          <p>{{ nextActionSummary }}</p>
        </div>

        <div class="summary-grid">
          <div class="summary-item">
            <span>任务类型</span>
            <strong>{{ taskStore.currentTask.taskType }}</strong>
          </div>
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
          <div class="summary-item">
            <span>批次状态</span>
            <strong>{{ batchStatusLabel }}</strong>
          </div>
          <div class="summary-item">
            <span>阻断项</span>
            <strong>{{ taskStore.blockers.length }}</strong>
          </div>
          <div class="summary-item">
            <span>就绪模块</span>
            <strong>{{ completedStepCount }}/{{ setupSteps.length }}</strong>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useConfigStore } from "../stores/config";
import { useTaskContextStore } from "../stores/task-context";

const router = useRouter();
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

const currentAnswer = computed(() => configStore.answers.find((item) => item.current) ?? configStore.answers[0] ?? null);
const currentAnswerStatus = computed(() => currentAnswer.value?.status ?? "missing");
const currentRubricStatus = computed(() => configStore.currentRubric?.status ?? "missing");
const currentTemplateStatus = computed(() => configStore.currentTemplate?.status ?? "missing");

const workspaceStatusLabel = computed(() => {
  const map: Record<string, string> = {
    unchecked: "未检测",
    valid: "检测通过",
    invalid: "检测失败",
    initializing: "初始化中",
  };
  return map[configStore.workspace?.status ?? "unchecked"];
});

const statusTone = (status: string) => {
  if (status === "in_use" || status === "confirmed" || status === "valid") return "status-badge--good";
  if (status === "draft" || status === "initializing" || status === "unchecked") return "status-badge--warn";
  return "status-badge--risk";
};

const statusText = (status: string) => {
  const map: Record<string, string> = {
    missing: "未配置",
    draft: "草稿",
    confirmed: "已确认",
    in_use: "使用中",
    parse_failed: "解析失败",
  };
  return map[status] ?? status;
};

const setupSteps = computed(() => {
  if (!taskStore.currentTask) return [];

  return [
    {
      id: "students",
      index: "01",
      title: "班级与学生",
      description: "确认班级、学生人数和提交进度。",
      status: "已同步",
      tone: "status-badge--good",
      summary: `${taskStore.currentTask.className} · 学生 ${taskStore.currentTask.studentCount} 人 · 已提交 ${taskStore.currentTask.submittedCount} 人`,
      action: "查看课程工作台",
      to: { name: "course-workspace", params: { courseName: taskStore.currentTask.courseName } },
      hint: "",
      ready: true,
    },
    {
      id: "answers",
      index: "02",
      title: "标准答案",
      description: "确认当前启用版本、解析状态和条目数。",
      status: statusText(currentAnswerStatus.value),
      tone: statusTone(currentAnswerStatus.value),
      summary: currentAnswer.value
        ? `${currentAnswer.value.fileName} · ${currentAnswer.value.version} · ${currentAnswer.value.itemCount} 项`
        : "当前任务尚未上传或激活标准答案版本。",
      action: "去配置标准答案",
      to: { name: "task-answers", params: { taskId: taskStore.currentTask.id } },
      hint: currentAnswer.value?.parseMessage ?? "",
      ready: currentAnswerStatus.value === "confirmed" || currentAnswerStatus.value === "in_use",
    },
    {
      id: "rubric",
      index: "03",
      title: "评分标准",
      description: "绑定适配当前任务的 Rubric，并确认结构完整。",
      status: statusText(currentRubricStatus.value),
      tone: statusTone(currentRubricStatus.value),
      summary: configStore.currentRubric
        ? `${configStore.currentRubric.name} · ${configStore.currentRubric.version}`
        : "当前任务尚未绑定评分标准。",
      action: "去配置 Rubric",
      to: { name: "task-rubrics", params: { taskId: taskStore.currentTask.id } },
      hint: configStore.currentRubric?.warnings[0] ?? "",
      ready: currentRubricStatus.value === "confirmed" || currentRubricStatus.value === "in_use",
    },
    {
      id: "template",
      index: "04",
      title: "导出模板",
      description: "检查 Excel 模板版本和已启用字段。",
      status: statusText(currentTemplateStatus.value),
      tone: statusTone(currentTemplateStatus.value),
      summary: configStore.currentTemplate
        ? `${configStore.currentTemplate.name} · ${configStore.currentTemplate.version}`
        : "当前任务尚未绑定 Excel 模板。",
      action: "去配置模板",
      to: { name: "task-template", params: { taskId: taskStore.currentTask.id } },
      hint: "",
      ready: currentTemplateStatus.value === "confirmed" || currentTemplateStatus.value === "in_use",
    },
    {
      id: "workspace",
      index: "05",
      title: "工作区路径",
      description: "检测原始数据、IR、得分和导出目录是否可用。",
      status: workspaceStatusLabel.value,
      tone: statusTone(configStore.workspace?.status ?? "unchecked"),
      summary: configStore.workspace
        ? `${configStore.workspace.rootPath} · ${configStore.workspace.lastMessage ?? "等待检测"}`
        : "当前任务尚未加载工作区路径配置。",
      action: "去检查路径",
      to: { name: "task-workspace", params: { taskId: taskStore.currentTask.id } },
      hint: configStore.workspace?.lastCheckedAt ? `最近检测：${configStore.workspace.lastCheckedAt}` : "",
      ready: configStore.workspace?.status === "valid",
    },
  ];
});

const completedStepCount = computed(() => setupSteps.value.filter((step) => step.ready).length);
const pendingSteps = computed(() => setupSteps.value.filter((step) => !step.ready));
const readySteps = computed(() => setupSteps.value.filter((step) => step.ready));
const blockerSummary = computed(() => taskStore.blockers.map((item) => item.title).join("；"));

const nextActionSummary = computed(() => {
  const firstPending = setupSteps.value.find((step) => !step.ready);
  if (!firstPending) return "配置已完整，可以直接进入批量阅卷页面。";
  return `建议先完成“${firstPending.title}”，再重新检查是否满足执行条件。`;
});

const batchStatusLabel = computed(() => {
  if (!taskStore.currentTask) return "";
  const map: Record<string, string> = {
    idle: "待开始",
    preprocessing: "预处理中",
    scoring: "评分中",
    aggregating: "汇总中",
    completed: "已完成",
    failed: "执行失败",
  };
  return map[taskStore.currentTask.batchStatus] ?? taskStore.currentTask.batchStatus;
});

const goToGrading = async () => {
  if (!taskStore.currentTask) return;
  await router.push({ name: "task-grading", params: { taskId: taskStore.currentTask.id } });
};
</script>
