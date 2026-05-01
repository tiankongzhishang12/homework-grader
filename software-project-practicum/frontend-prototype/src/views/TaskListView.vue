<template>
  <section class="view">
    <div class="hero-card hero-card--dense">
      <div>
        <div class="eyebrow">课程入口</div>
        <h2 class="hero-card__title">先确定课程，再进入班级和任务</h2>
        <p class="hero-card__text">
          首页只负责帮老师快速定位当前要处理的课程。进入课程后，再按班级和任务推进配置、阅卷、分析和导出。
        </p>
      </div>
      <div class="hero-card__meta hero-card__meta--summary">
        <span class="pill pill--good">课程 {{ filteredCourses.length }}</span>
        <span class="pill">{{ selectedCourseSummary?.courseName ?? "未选择课程" }}</span>
        <span class="pill pill--warn">待补配置 {{ pendingTaskCount }}</span>
      </div>
    </div>

    <section class="panel panel--compact">
      <div class="filter-toolbar course-filter-bar">
        <div class="select-mock">
          <span class="select-mock__label">学年</span>
          <select v-model="academicYear" class="selector-select">
            <option value="all">全部</option>
            <option v-for="item in academicYearOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>
        <div class="select-mock">
          <span class="select-mock__label">学期</span>
          <select v-model="semester" class="selector-select">
            <option value="all">全部</option>
            <option value="1">第一学期</option>
            <option value="2">第二学期</option>
          </select>
        </div>
        <div class="select-mock">
          <span class="select-mock__label">状态</span>
          <select v-model="courseStatus" class="selector-select">
            <option value="all">全部</option>
            <option value="not_ready">待补配置</option>
            <option value="idle">待开始</option>
            <option value="running">评分中</option>
            <option value="completed">已完成</option>
          </select>
        </div>
        <div class="select-mock">
          <span class="select-mock__label">排序</span>
          <select v-model="sortBy" class="selector-select">
            <option value="recent">最近访问优先</option>
            <option value="tasks">任务数优先</option>
            <option value="name">课程名称</option>
          </select>
        </div>
        <input v-model="keyword" class="field__input field__input--search" type="text" placeholder="搜索课程名或课程代码" />
      </div>
    </section>

    <section v-if="taskStore.tasks.length === 0" class="panel">
      <div class="empty-state">
        当前暂无课程数据。请先刷新课程列表，或等待后端接口返回可见课程、班级与任务信息。
      </div>
      <div class="toolbar__actions">
        <button class="action-button" :disabled="taskStore.loading" @click="taskStore.loadTasks()">
          {{ taskStore.loading ? "刷新中..." : "刷新课程列表" }}
        </button>
      </div>
    </section>

    <div v-else class="course-home-layout course-home-layout--refined">
      <section class="panel">
        <div class="panel__header">
          <div>
            <h3>课程列表</h3>
            <p class="panel__description">单击选择课程，点击按钮进入课程工作台。</p>
          </div>
          <span class="pill">{{ filteredCourses.length }} 门课程</span>
        </div>

        <div v-if="filteredCourses.length > 0" class="course-card-list">
          <article
            v-for="course in filteredCourses"
            :key="course.courseName"
            class="course-card"
            :class="{ 'course-card--active': taskStore.selectedCourseName === course.courseName }"
            @click="taskStore.setSelectedCourse(course.courseName)"
          >
            <div class="course-card__main">
              <div class="course-card__cover">{{ course.courseName.slice(0, 2) }}</div>
              <div class="course-card__body">
                <div class="course-card__title-row">
                  <div>
                    <div class="course-card__title">{{ course.courseName }}</div>
                    <div class="course-card__meta">{{ course.courseCode }} · {{ formatTerm(course.term) }}</div>
                  </div>
                  <span class="status-badge" :class="statusClassMap[course.status]">{{ courseStatusMap[course.status] }}</span>
                </div>
                <div class="course-card__info">
                  <span>班级 {{ course.classCount }}</span>
                  <span>学生 {{ course.totalStudents }}</span>
                  <span>任务 {{ course.taskCount }}</span>
                  <span>可直接开始 {{ course.readyTaskCount }}</span>
                </div>
                <p class="course-card__summary">{{ course.recentBatchSummary }}</p>
              </div>
            </div>
            <div class="course-card__aside">
              <span class="pill">{{ runningSummary(course) }}</span>
              <button class="action-button" @click.stop="enterCourse(course.courseName)">进入课程</button>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">没有符合当前筛选条件的课程。</div>
      </section>

      <section class="panel course-summary-panel">
        <div v-if="selectedCourseSummary" class="course-summary-panel__body">
          <div class="panel__header panel__header--stack">
            <div>
              <h3>{{ selectedCourseSummary.courseName }}</h3>
              <p class="panel__description">当前选中课程的摘要与下一步入口。</p>
            </div>
            <button class="action-button" @click="enterCourse(selectedCourseSummary.courseName)">进入课程工作台</button>
          </div>

          <div class="stats-grid stats-grid--compact">
            <article class="stat-card stat-card--neutral">
              <div class="stat-card__label">班级数</div>
              <div class="stat-card__value">{{ selectedCourseSummary.classCount }}</div>
            </article>
            <article class="stat-card stat-card--neutral">
              <div class="stat-card__label">任务数</div>
              <div class="stat-card__value">{{ selectedCourseSummary.taskCount }}</div>
            </article>
            <article class="stat-card stat-card--warn">
              <div class="stat-card__label">待补配置</div>
              <div class="stat-card__value">{{ pendingTaskCount }}</div>
            </article>
          </div>

          <article class="notice-card">
            {{ selectedCourseSummary.recentBatchSummary }}
          </article>

          <div class="summary-grid">
            <div class="summary-item">
              <span>课程代码</span>
              <strong>{{ selectedCourseSummary.courseCode }}</strong>
            </div>
            <div class="summary-item">
              <span>开课学期</span>
              <strong>{{ formatTerm(selectedCourseSummary.term) }}</strong>
            </div>
            <div class="summary-item">
              <span>总学生数</span>
              <strong>{{ selectedCourseSummary.totalStudents }}</strong>
            </div>
            <div class="summary-item">
              <span>当前状态</span>
              <strong>{{ courseStatusMap[selectedCourseSummary.status] }}</strong>
            </div>
          </div>

          <div class="course-summary-panel__section">
            <h4>授课班级</h4>
            <div class="tag-row">
              <span v-for="item in selectedCourseSummary.classes" :key="item.className" class="tag">
                {{ item.className }} · {{ item.studentCount }} 人
              </span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">先从左侧课程列表中选择一门课程。</div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useTaskContextStore } from "../stores/task-context";
import type { CourseSummary } from "../types";

const taskStore = useTaskContextStore();
const router = useRouter();

const academicYear = ref("all");
const semester = ref("all");
const courseStatus = ref<"all" | "not_ready" | "idle" | "running" | "completed">("all");
const sortBy = ref<"recent" | "tasks" | "name">("recent");
const keyword = ref("");

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
  not_ready: "status-badge--warn",
  idle: "status-badge--good",
  running: "status-badge--warn",
  completed: "status-badge--good",
} as const;

const courseStatusMap = {
  not_ready: "待补配置",
  idle: "待开始",
  running: "评分中",
  completed: "已完成",
} as const;

onMounted(async () => {
  if (taskStore.tasks.length === 0) {
    await taskStore.loadTasks();
  } else {
    taskStore.syncSelection();
  }
});

const academicYearOptions = computed(() =>
  [...new Set(taskStore.courseGroups.map((item) => parseTerm(item.term).year))].filter(Boolean).sort((a, b) => b.localeCompare(a, "zh-CN")),
);

const filteredCourses = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  const filtered = taskStore.courseGroups.filter((item) => {
    const { year, semester: semesterValue } = parseTerm(item.term);
    const matchesKeyword = !value || item.courseName.toLowerCase().includes(value) || item.courseCode.toLowerCase().includes(value);
    const matchesYear = academicYear.value === "all" || academicYear.value === year;
    const matchesSemester = semester.value === "all" || semester.value === semesterValue;
    const matchesStatus = courseStatus.value === "all" || courseStatus.value === item.status;
    return matchesKeyword && matchesYear && matchesSemester && matchesStatus;
  });

  if (sortBy.value === "name") {
    return [...filtered].sort((a, b) => a.courseName.localeCompare(b.courseName, "zh-CN"));
  }
  if (sortBy.value === "tasks") {
    return [...filtered].sort((a, b) => b.taskCount - a.taskCount || a.courseName.localeCompare(b.courseName, "zh-CN"));
  }
  return [...filtered].sort((a, b) => {
    if (a.courseName === taskStore.selectedCourseName) return -1;
    if (b.courseName === taskStore.selectedCourseName) return 1;
    return b.term.localeCompare(a.term, "zh-CN") || a.courseName.localeCompare(b.courseName, "zh-CN");
  });
});

watch(
  filteredCourses,
  (courses) => {
    if (courses.length === 0) return;
    if (!courses.some((item) => item.courseName === taskStore.selectedCourseName)) {
      taskStore.setSelectedCourse(courses[0].courseName);
    }
  },
  { immediate: true },
);

const selectedCourseSummary = computed<CourseSummary | null>(() => taskStore.selectedCourseSummary);
const pendingTaskCount = computed(() => {
  if (!selectedCourseSummary.value) return 0;
  return selectedCourseSummary.value.taskCount - selectedCourseSummary.value.readyTaskCount;
});

const runningSummary = (course: CourseSummary) => {
  if (course.runningTaskCount > 0) return `${course.runningTaskCount} 个任务评分中`;
  if (course.completedTaskCount > 0) return `${course.completedTaskCount} 个任务已完成`;
  return `${course.readyTaskCount} 个任务可直接开始`;
};

const enterCourse = async (courseName: string) => {
  taskStore.setSelectedCourse(courseName);
  await router.push({ name: "course-workspace", params: { courseName } });
};
</script>
