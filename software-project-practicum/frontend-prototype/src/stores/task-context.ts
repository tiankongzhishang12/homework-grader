import { defineStore } from "pinia";
import { taskApi } from "../api/services";
import type { ConfigBlocker, CourseStatus, TaskCourseGroup, TaskDetail } from "../types";

const TASK_SELECTION_KEY = "grader-task-selection-v1";

const readSavedSelection = () => {
  const raw = window.localStorage.getItem(TASK_SELECTION_KEY);
  if (!raw) return { courseName: null as string | null, className: null as string | null };
  try {
    return JSON.parse(raw) as { courseName: string | null; className: string | null };
  } catch {
    return { courseName: null as string | null, className: null as string | null };
  }
};

const persistSelection = (courseName: string | null, className: string | null) => {
  window.localStorage.setItem(TASK_SELECTION_KEY, JSON.stringify({ courseName, className }));
};

const runningStatuses = ["preprocessing", "scoring", "aggregating"] as const;

const summarizeCourseStatus = (tasks: TaskDetail[]): CourseStatus => {
  if (tasks.some((task) => runningStatuses.includes(task.batchStatus))) return "running";
  if (tasks.length > 0 && tasks.every((task) => task.batchStatus === "completed")) return "completed";
  if (tasks.some((task) => !task.configReady)) return "not_ready";
  return "idle";
};

const buildRecentBatchSummary = (tasks: TaskDetail[]) => {
  const runningCount = tasks.filter((task) => runningStatuses.includes(task.batchStatus)).length;
  const completedCount = tasks.filter((task) => task.batchStatus === "completed").length;
  const notReadyCount = tasks.filter((task) => !task.configReady).length;

  if (runningCount > 0) return `当前有 ${runningCount} 个任务正在阅卷`;
  if (completedCount > 0) return `最近已完成 ${completedCount} 个任务的评分`;
  if (notReadyCount > 0) return `仍有 ${notReadyCount} 个任务待补配置`;
  return "当前课程已经具备开始阅卷的基础条件";
};

const groupTasksByCourse = (tasks: TaskDetail[]): TaskCourseGroup[] => {
  const courseMap = new Map<string, Map<string, TaskDetail[]>>();

  tasks.forEach((task) => {
    if (!courseMap.has(task.courseName)) {
      courseMap.set(task.courseName, new Map<string, TaskDetail[]>());
    }
    const classMap = courseMap.get(task.courseName)!;
    if (!classMap.has(task.className)) {
      classMap.set(task.className, []);
    }
    classMap.get(task.className)!.push(task);
  });

  return [...courseMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b, "zh-CN"))
    .map(([courseName, classMap]) => {
      const allTasks = [...classMap.values()].flat();
      const classes = [...classMap.entries()]
        .sort(([a], [b]) => a.localeCompare(b, "zh-CN"))
        .map(([className, classTasks]) => ({
          className,
          studentCount: Math.max(...classTasks.map((task) => task.studentCount)),
          submittedCount: Math.max(...classTasks.map((task) => task.submittedCount)),
          activeTaskCount: classTasks.filter((task) => runningStatuses.includes(task.batchStatus)).length,
          tasks: classTasks.sort((a, b) => a.taskName.localeCompare(b.taskName, "zh-CN")),
        }));

      return {
        courseName,
        courseCode: allTasks[0]?.courseCode ?? "",
        term: allTasks[0]?.term ?? "",
        status: summarizeCourseStatus(allTasks),
        recentBatchSummary: buildRecentBatchSummary(allTasks),
        classCount: classes.length,
        totalStudents: classes.reduce((sum, item) => sum + item.studentCount, 0),
        taskCount: allTasks.length,
        readyTaskCount: allTasks.filter((task) => task.configReady).length,
        runningTaskCount: allTasks.filter((task) => runningStatuses.includes(task.batchStatus)).length,
        completedTaskCount: allTasks.filter((task) => task.batchStatus === "completed").length,
        classes,
      };
    });
};

export const useTaskContextStore = defineStore("task-context", {
  state: () => ({
    tasks: [] as TaskDetail[],
    currentTask: null as TaskDetail | null,
    blockers: [] as ConfigBlocker[],
    loading: false,
    selectedCourseName: null as string | null,
    selectedClassName: null as string | null,
  }),
  getters: {
    currentTaskId: (state) => state.currentTask?.id ?? null,
    currentAssessmentId: (state) => state.currentTask?.assessmentId ?? state.currentTask?.id ?? null,
    currentTemplateId: (state) => state.currentTask?.templateId ?? null,
    currentQuestionId: (state) => state.currentTask?.questionId ?? null,
    canStartBatch: (state) => state.blockers.length === 0,
    groupedTasks: (state): TaskCourseGroup[] => groupTasksByCourse(state.tasks),
    courseGroups(): TaskCourseGroup[] {
      return this.groupedTasks;
    },
    selectedCourseSummary(): TaskCourseGroup | null {
      return this.groupedTasks.find((item) => item.courseName === this.selectedCourseName) ?? null;
    },
    visibleClasses() {
      return this.selectedCourseSummary?.classes ?? [];
    },
    visibleTasks() {
      const current = this.visibleClasses.find((item) => item.className === this.selectedClassName);
      return current?.tasks ?? [];
    },
  },
  actions: {
    syncSelection(preferredCourseName?: string | null) {
      const groups = this.groupedTasks;
      if (groups.length === 0) {
        this.selectedCourseName = null;
        this.selectedClassName = null;
        persistSelection(null, null);
        return;
      }

      const saved = readSavedSelection();
      const course =
        groups.find((item) => item.courseName === preferredCourseName) ??
        groups.find((item) => item.courseName === this.selectedCourseName) ??
        groups.find((item) => item.courseName === saved.courseName) ??
        groups[0];

      this.selectedCourseName = course.courseName;

      const nextClass =
        course.classes.find((item) => item.className === this.selectedClassName) ??
        course.classes.find((item) => item.className === saved.className) ??
        course.classes[0] ??
        null;

      this.selectedClassName = nextClass?.className ?? null;
      persistSelection(this.selectedCourseName, this.selectedClassName);
    },
    setSelectedCourse(courseName: string) {
      this.selectedCourseName = courseName;
      const course = this.groupedTasks.find((item) => item.courseName === courseName);
      if (!course) {
        this.selectedClassName = null;
      } else if (!course.classes.some((item) => item.className === this.selectedClassName)) {
        this.selectedClassName = course.classes[0]?.className ?? null;
      }
      persistSelection(this.selectedCourseName, this.selectedClassName);
    },
    setSelectedClass(className: string) {
      this.selectedClassName = className;
      persistSelection(this.selectedCourseName, this.selectedClassName);
    },
    selectCourseFromRoute(courseName: string) {
      if (!this.groupedTasks.some((item) => item.courseName === courseName)) {
        this.syncSelection();
        return false;
      }
      this.setSelectedCourse(courseName);
      return true;
    },
    async loadTasks() {
      this.loading = true;
      try {
        this.tasks = await taskApi.list();
        this.syncSelection();
      } finally {
        this.loading = false;
      }
    },
    async loadTask(taskId: string) {
      this.loading = true;
      try {
        this.currentTask = await taskApi.get(taskId);
        const { blockers } = await taskApi.blockers(taskId);
        this.blockers = blockers;
        const index = this.tasks.findIndex((item) => item.id === taskId);
        if (index >= 0 && this.currentTask) {
          this.tasks[index] = this.currentTask;
        }
        if (this.currentTask) {
          this.syncSelection(this.currentTask.courseName);
          this.selectedClassName = this.currentTask.className;
          persistSelection(this.selectedCourseName, this.selectedClassName);
        }
      } finally {
        this.loading = false;
      }
    },
    async refreshBlockers(taskId?: string) {
      const target = taskId ?? this.currentTask?.id;
      if (!target) return;
      const { blockers } = await taskApi.blockers(target);
      this.blockers = blockers;
      const latestTask = await taskApi.get(target);
      this.currentTask = latestTask;
      const index = this.tasks.findIndex((item) => item.id === target);
      if (index >= 0) {
        this.tasks[index] = latestTask;
      }
      this.syncSelection(latestTask.courseName);
      this.selectedClassName = latestTask.className;
      persistSelection(this.selectedCourseName, this.selectedClassName);
    },
  },
});
