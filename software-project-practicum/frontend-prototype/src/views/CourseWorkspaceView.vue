<template>
  <section class="view" v-if="courseSummary">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">课程工作台</div>
        <h2 class="hero-card__title">{{ courseSummary.courseName }}</h2>
        <p class="hero-card__text">
          先确定班级，再从当前班级里选择具体任务。右侧会固定显示当前选中任务的摘要和下一步动作，减少来回跳转的判断成本。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill">{{ courseSummary.courseCode }}</span>
        <span class="pill">{{ formatTerm(courseSummary.term) }}</span>
        <span class="pill" :class="statusClassMap[courseSummary.status]">{{ courseStatusMap[courseSummary.status] }}</span>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card stat-card--good">
        <div class="stat-card__label">班级数</div>
        <div class="stat-card__value">{{ courseSummary.classCount }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">当前班级学生数</div>
        <div class="stat-card__value">{{ selectedClassSummary?.studentCount ?? 0 }}</div>
      </article>
      <article class="stat-card stat-card--neutral">
        <div class="stat-card__label">当前班级任务数</div>
        <div class="stat-card__value">{{ filteredTasks.length }}</div>
      </article>
      <article class="stat-card stat-card--warn">
        <div class="stat-card__label">进行中任务</div>
        <div class="stat-card__value">{{ selectedClassSummary?.activeTaskCount ?? 0 }}</div>
      </article>
    </div>

    <div class="workspace-flow-grid">
      <section class="panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>1. 选择班级</h3>
            <p class="panel__description">先定位老师当前要处理的班级，再进入该班级下的作业或考试任务。</p>
          </div>
          <input v-model="classKeyword" class="field__input" type="text" placeholder="搜索班级名称" />
        </div>

        <div v-if="filteredClasses.length > 0" class="selector-list">
          <button
            v-for="item in filteredClasses"
            :key="item.className"
            class="selector-item selector-item--class"
            :class="{ 'selector-item--active': taskStore.selectedClassName === item.className }"
            @click="taskStore.setSelectedClass(item.className)"
          >
            <div class="selector-item__title">{{ item.className }}</div>
            <div class="selector-item__meta">
              学生 {{ item.studentCount }} · 已提交 {{ item.submittedCount }} · 进行中 {{ item.activeTaskCount }}
            </div>
          </button>
        </div>
        <div v-else class="empty-state empty-state--small">当前课程下暂无符合筛选条件的班级。</div>
      </section>

      <section class="panel selector-panel--tasks">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>2. 选择任务</h3>
            <p class="panel__description">只展示当前班级下的任务，帮助老师尽快定位本次要处理的那一项。</p>
          </div>
          <div class="filter-toolbar">
            <input v-model="taskKeyword" class="field__input field__input--search" type="text" placeholder="搜索任务名称" />
            <div class="select-mock">
              <span class="select-mock__label">类型</span>
              <select v-model="taskKind" class="selector-select">
                <option value="all">全部</option>
                <option value="assignment">作业</option>
                <option value="exam">考试</option>
              </select>
            </div>
            <div class="select-mock">
              <span class="select-mock__label">状态</span>
              <select v-model="taskStatus" class="selector-select">
                <option value="all">全部</option>
                <option value="not_ready">待补配置</option>
                <option value="idle">待开始</option>
                <option value="running">评分中</option>
                <option value="completed">已完成</option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="filteredTasks.length === 0" class="empty-state">当前班级暂无符合筛选条件的任务。</div>
        <div v-else class="task-card-stack">
          <article
            v-for="task in filteredTasks"
            :key="task.id"
            class="task-list-card"
            :class="{ 'task-list-card--active': selectedTask?.id === task.id }"
            @click="selectedTaskId = task.id"
          >
            <div class="task-list-card__top">
              <div>
                <div class="rubric-card__title">{{ task.taskName }}</div>
                <div class="rubric-card__meta">{{ task.className }} · {{ task.taskType }}</div>
              </div>
              <span class="status-badge" :class="task.configReady ? 'status-badge--good' : 'status-badge--warn'">
                {{ task.configReady ? "配置已就绪" : "待补配置" }}
              </span>
            </div>

            <p class="rubric-card__summary">{{ task.description }}</p>

            <div class="summary-grid">
              <div class="summary-item">
                <span>提交进度</span>
                <strong>{{ task.submittedCount }}/{{ task.studentCount }}</strong>
              </div>
              <div class="summary-item">
                <span>配置完成度</span>
                <strong>{{ task.configProgress }}%</strong>
              </div>
              <div class="summary-item">
                <span>批次状态</span>
                <strong>{{ batchStatusMap[task.batchStatus] }}</strong>
              </div>
              <div class="summary-item">
                <span>下一步</span>
                <strong>{{ task.nextAction }}</strong>
              </div>
            </div>
          </article>
        </div>
      </section>

      <aside class="panel workspace-summary-panel">
        <div class="panel__header panel__header--stack">
          <div>
            <h3>3. 当前任务摘要</h3>
            <p class="panel__description">确认这项任务的就绪度后，直接进入配置或查看最近结果。</p>
          </div>
          <RouterLink
            v-if="selectedTask"
            :to="{ name: 'task-config', params: { taskId: selectedTask.id } }"
            class="action-button"
          >
            进入任务配置
          </RouterLink>
          <button v-else class="action-button" disabled>进入任务配置</button>
        </div>

        <div v-if="selectedTask" class="workspace-summary-panel__body">
          <div class="detail-block detail-block--highlight">
            <h4>{{ selectedTask.taskName }}</h4>
            <p>{{ selectedTask.description }}</p>
          </div>

          <div class="summary-grid">
            <div class="summary-item">
              <span>任务类型</span>
              <strong>{{ selectedTask.taskType }}</strong>
            </div>
            <div class="summary-item">
              <span>班级</span>
              <strong>{{ selectedTask.className }}</strong>
            </div>
            <div class="summary-item">
              <span>配置完成度</span>
              <strong>{{ selectedTask.configProgress }}%</strong>
            </div>
            <div class="summary-item">
              <span>批次状态</span>
              <strong>{{ batchStatusMap[selectedTask.batchStatus] }}</strong>
            </div>
          </div>

          <div class="tag-row">
            <span class="tag">{{ classifyTask(selectedTask) === "exam" ? "考试" : "作业" }}</span>
            <span class="tag" :class="selectedTask.configReady ? 'tag--good' : 'tag--warn'">
              {{ selectedTask.configReady ? "可直接进入配置检查" : "建议先补齐配置" }}
            </span>
          </div>

          <div class="workspace-summary-panel__actions">
            <RouterLink :to="{ name: 'task-config', params: { taskId: selectedTask.id } }" class="action-button action-button--ghost">
              检查任务配置
            </RouterLink>
            <RouterLink
              v-if="selectedTask.batchStatus === 'completed'"
              :to="{ name: 'task-analysis', params: { taskId: selectedTask.id } }"
              class="action-button action-button--ghost"
            >
              查看结果分析
            </RouterLink>
            <RouterLink
              v-else-if="latestResultTask"
              :to="{ name: 'task-analysis', params: { taskId: latestResultTask.id } }"
              class="action-button action-button--ghost"
            >
              查看最近完成结果
            </RouterLink>
            <button v-else class="action-button action-button--ghost" disabled>暂无可查看结果</button>
          </div>
        </div>

        <div v-else class="empty-state">先从中间列表中选择一项任务。</div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useTaskContextStore } from "../stores/task-context";
import type { TaskDetail } from "../types";

const route = useRoute();
const router = useRouter();
const taskStore = useTaskContextStore();

const classKeyword = ref("");
const taskKeyword = ref("");
const taskKind = ref<"all" | "assignment" | "exam">("all");
const taskStatus = ref<"all" | "not_ready" | "idle" | "running" | "completed">("all");
const selectedTaskId = ref<string | null>(null);

const parseTerm = (term: string) => {
  const match = term.match(/^(\d{4}-\d{4})-(\d)$/);
  return {
    year: match?.[1] ?? term,
    semester: match?.[2] ?? "",
  };
};

const formatTerm = (term: string) => {
  const { year, semester: semesterValue } = parseTerm(term);
  return semesterValue ? `${year} 第${semesterValue}学期` : year;
};

const statusClassMap = {
  not_ready: "pill--warn",
  idle: "pill--good",
  running: "pill--warn",
  completed: "pill--good",
} as const;

const courseStatusMap = {
  not_ready: "待补配置",
  idle: "待开始",
  running: "评分中",
  completed: "已完成",
} as const;

const batchStatusMap = {
  idle: "待开始",
  preprocessing: "预处理中",
  scoring: "评分中",
  aggregating: "汇总中",
  completed: "已完成",
  failed: "执行失败",
} as const;

const classifyTask = (task: TaskDetail) => {
  const label = `${task.taskName} ${task.taskType}`;
  return label.includes("考试") || label.includes("测验") ? "exam" : "assignment";
};

const syncCourseFromRoute = async () => {
  if (taskStore.tasks.length === 0) {
    await taskStore.loadTasks();
  }
  const targetCourseName = String(route.params.courseName ?? "");
  if (!targetCourseName) {
    await router.replace({ name: "tasks" });
    return;
  }
  const matched = taskStore.selectCourseFromRoute(targetCourseName);
  if (!matched) {
    await router.replace({ name: "tasks" });
  }
};

onMounted(async () => {
  await syncCourseFromRoute();
});

watch(
  () => route.params.courseName,
  async () => {
    await syncCourseFromRoute();
  },
);

const courseSummary = computed(() => taskStore.selectedCourseSummary);
const selectedClassSummary = computed(() => taskStore.visibleClasses.find((item) => item.className === taskStore.selectedClassName) ?? null);

const filteredClasses = computed(() => {
  const value = classKeyword.value.trim().toLowerCase();
  if (!value) return taskStore.visibleClasses;
  return taskStore.visibleClasses.filter((item) => item.className.toLowerCase().includes(value));
});

const filteredTasks = computed(() => {
  const keyword = taskKeyword.value.trim().toLowerCase();
  return taskStore.visibleTasks.filter((task) => {
    const matchesKeyword = !keyword || task.taskName.toLowerCase().includes(keyword);
    const matchesKind = taskKind.value === "all" || classifyTask(task) === taskKind.value;
    const matchesStatus =
      taskStatus.value === "all" ||
      (taskStatus.value === "not_ready" && !task.configReady) ||
      (taskStatus.value === "idle" && task.batchStatus === "idle") ||
      (taskStatus.value === "running" && ["preprocessing", "scoring", "aggregating"].includes(task.batchStatus)) ||
      (taskStatus.value === "completed" && task.batchStatus === "completed");
    return matchesKeyword && matchesKind && matchesStatus;
  });
});

watch(
  filteredTasks,
  (tasks) => {
    if (tasks.length === 0) {
      selectedTaskId.value = null;
      return;
    }
    if (!tasks.some((item) => item.id === selectedTaskId.value)) {
      selectedTaskId.value = tasks[0].id;
    }
  },
  { immediate: true },
);

const selectedTask = computed(() => filteredTasks.value.find((item) => item.id === selectedTaskId.value) ?? filteredTasks.value[0] ?? null);
const latestResultTask = computed(() => taskStore.visibleTasks.find((item) => item.batchStatus === "completed") ?? selectedTask.value);
</script>
