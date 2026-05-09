import { defineStore } from "pinia";
import { ApiError } from "../api/client";
import { batchApi, exportApi, finalResultApi, gradingApi, resultApi, submissionApi } from "../api/services";
import type {
  AnalysisSummary,
  BatchLog,
  BatchProgress,
  ExportRecord,
  FinalResultRecord,
  GradingProgressResponse,
  ScoreItemRecord,
  StudentDetail,
  StudentRow,
  TaskDetail,
  User,
} from "../types";
import { useAuthStore } from "./auth";
import { useTaskContextStore } from "./task-context";
import { useUiStore } from "./ui";

let pollTimer: number | null = null;

const toText = (value: unknown, fallback = "") => (value === null || value === undefined ? fallback : String(value));

const toNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const resolveAssessmentId = (task: TaskDetail | null) => {
  if (!task) return null;
  // TODO: replace this fallback once /api/tasks explicitly returns assessmentId for every real task row.
  return task.assessmentId ?? task.id;
};

const resolveTeacherId = (user: User | null) => {
  if (!user) return null;
  return user.teacherId ?? user.id ?? null;
};

const mapRealStatusToBatchStatus = (status?: string): BatchProgress["status"] => {
  switch (status) {
    case "QUEUED":
    case "PREPROCESSING":
      return "preprocessing";
    case "GRADING":
      return "scoring";
    case "COMPLETED":
      return "completed";
    case "FAILED":
      return "failed";
    default:
      return "idle";
  }
};

const toStepLabel = (progress: GradingProgressResponse) => {
  if (progress.message) return progress.message;
  switch (progress.status) {
    case "QUEUED":
      return "任务已排队，等待进入预处理。";
    case "PREPROCESSING":
      return "正在执行预处理。";
    case "GRADING":
      return "正在执行评分与结果导入。";
    case "COMPLETED":
      return "评分与结果导入已完成。";
    case "FAILED":
      return "评分流程失败，请查看后端日志。";
    default:
      return "等待开始阅卷。";
  }
};

const mapProgress = (taskId: string, progress: GradingProgressResponse): BatchProgress => {
  const summary = progress.importSummary ?? {};
  const imported = toNumber(summary.importedCount);
  const skipped = toNumber(summary.skippedCount);
  const failed = toNumber(summary.failedCount);
  const qualityFlags: BatchProgress["qualityFlags"] = [];
  if (skipped > 0) qualityFlags.push({ flag: "traceability_gap", count: skipped, label: "导入跳过" });
  if (failed > 0) qualityFlags.push({ flag: "gate_warning", count: failed, label: "导入失败" });

  return {
    taskId,
    status: mapRealStatusToBatchStatus(progress.status),
    startedAt: progress.startedAt,
    updatedAt: progress.updatedAt ?? new Date().toISOString(),
    total: imported + skipped + failed,
    completed: imported,
    currentStepLabel: toStepLabel(progress),
    qualityFlags,
  };
};

const mapFinalResultToStudentRow = (assessmentId: string, row: FinalResultRecord): StudentRow => {
  const studentId = toText(row.studentId ?? row.student_id, "");
  const submissionId = toText(row.submissionId ?? row.submission_id, "");
  const finalResultId = toText(row.id);
  const reviewStatus = toText(row.reviewStatus ?? row.review_status, "PENDING");
  const confidence = toNumber(row.overallConfidence ?? row.overall_confidence);
  const score = toNumber(row.finalScore ?? row.final_score);

  return {
    id: studentId || submissionId || finalResultId,
    assessmentId,
    submissionId,
    finalResultId,
    studentId,
    studentNumber: toText(row.studentNo ?? row.student_no, submissionId ? `submission:${submissionId}` : "-"),
    name: toText(row.studentName ?? row.student_name, studentId ? `student:${studentId}` : `final-result:${finalResultId}`),
    anonymousId: studentId || submissionId || finalResultId,
    score,
    grade: toText(row.grade, reviewStatus),
    confidence,
    gateStatus: reviewStatus,
    reviewStatus,
    confirmedAt: toText(row.confirmedAt ?? row.confirmed_at, ""),
    traceabilityGapCount: 0,
    consistencyIssueCount: reviewStatus === "ADJUSTED" ? 1 : 0,
    riskTags: [reviewStatus, ...(confidence > 0 && confidence < 0.8 ? ["LOW_CONFIDENCE"] : [])],
  };
};

const buildAnalytics = (students: StudentRow[]): AnalysisSummary => {
  const emptyBands = [
    { label: "<60", value: 0 },
    { label: "60-69", value: 0 },
    { label: "70-79", value: 0 },
    { label: "80-89", value: 0 },
    { label: "90+", value: 0 },
  ];

  if (students.length === 0) {
    return {
      averageScore: 0,
      totalStudents: 0,
      lowConfidenceCount: 0,
      gateWarningCount: 0,
      placeholderResidueCount: 0,
      scoreBands: emptyBands,
      topIssues: [],
    };
  }

  const averageScore = Number((students.reduce((sum, item) => sum + item.score, 0) / students.length).toFixed(1));
  const lowConfidenceCount = students.filter((item) => item.confidence > 0 && item.confidence < 0.8).length;
  const gateWarningCount = students.filter((item) => item.gateStatus !== "CONFIRMED").length;
  const reviewStatusCount = new Map<string, number>();
  students.forEach((item) => {
    const key = item.reviewStatus ?? "UNKNOWN";
    reviewStatusCount.set(key, (reviewStatusCount.get(key) ?? 0) + 1);
  });

  return {
    averageScore,
    totalStudents: students.length,
    lowConfidenceCount,
    gateWarningCount,
    placeholderResidueCount: 0,
    scoreBands: [
      { label: "<60", value: students.filter((item) => item.score < 60).length },
      { label: "60-69", value: students.filter((item) => item.score >= 60 && item.score < 70).length },
      { label: "70-79", value: students.filter((item) => item.score >= 70 && item.score < 80).length },
      { label: "80-89", value: students.filter((item) => item.score >= 80 && item.score < 90).length },
      { label: "90+", value: students.filter((item) => item.score >= 90).length },
    ],
    topIssues: [...reviewStatusCount.entries()].map(([title, count]) => ({
      title,
      count,
      detail: `共有 ${count} 条 final_result 处于 ${title} 状态。`,
    })),
  };
};

const normalizeEvidence = (item: ScoreItemRecord) => {
  if (item.evidence) return item.evidence;
  if (item.evidenceJson ?? item.evidence_json) return toText(item.evidenceJson ?? item.evidence_json);
  return "后端当前仅返回 score item 记录，未附带更详细证据摘要。";
};

const mapScoreItemsToStudentDetail = (
  assessmentId: string,
  student: StudentRow,
  scoreItems: ScoreItemRecord[],
): StudentDetail => ({
  id: student.id,
  assessmentId,
  submissionId: student.submissionId,
  finalResultId: student.finalResultId,
  studentId: student.studentId,
  name: student.name,
  studentNumber: student.studentNumber,
  anonymousId: student.anonymousId,
  score: student.score,
  percentileScore: student.score,
  grade: student.grade,
  confidence: student.confidence,
  reviewStatus: student.reviewStatus,
  confirmedAt: student.confirmedAt,
  summary: `submission ${student.submissionId} 的真实 score-items 已加载。当前 final_result 状态为 ${student.reviewStatus ?? "UNKNOWN"}。`,
  qualityFindings: [
    `final_result.review_status = ${student.reviewStatus ?? "UNKNOWN"}`,
    `submission_id = ${student.submissionId ?? "-"}`,
    `final_score = ${student.score}`,
  ],
  dimensions: scoreItems.map((item, index) => ({
    id: toText(item.criterionCode ?? item.criterion_code ?? item.id, `score-item-${index + 1}`),
    name: toText(item.criterionName ?? item.criterion_name, `Score Item ${index + 1}`),
    score: toNumber(item.score),
    maxScore: toNumber(item.maxScore ?? item.max_score),
    confidence: toNumber(item.confidence),
    evidence: normalizeEvidence(item),
    reasoning: toText(item.comment, "后端当前未提供更详细的结构化推理字段。"),
    matched: [],
    missing: [],
    improvement: "如需更丰富解释，需要后端继续补充 rubric / traceability 聚合字段。",
  })),
  traceability: {
    requirements: [],
    hldCoverage: [],
    lldCoverage: [],
    uncoveredRequirements: [],
  },
  gates: [
    {
      name: "Review Status",
      passed: student.reviewStatus === "CONFIRMED",
      detail: `当前状态：${student.reviewStatus ?? "UNKNOWN"}`,
      onFail: "建议教师确认或调整后再发布。",
    },
  ],
  materials: {
    documentCount: 0,
    wordCount: 0,
    imageCount: 0,
    roles: [],
    logs: ["score-items 接口当前未返回原始材料摘要字段。"],
  },
});

export const useBatchStore = defineStore("batch", {
  state: () => ({
    progress: null as BatchProgress | null,
    logs: [] as BatchLog[],
    students: [] as StudentRow[],
    analytics: null as AnalysisSummary | null,
    currentStudent: null as StudentDetail | null,
    exports: [] as ExportRecord[],
    loading: false,
    polling: false,
  }),
  actions: {
    stopPolling() {
      if (pollTimer) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }
      this.polling = false;
    },
    schedulePoll(taskId: string) {
      this.stopPolling();
      this.polling = true;
      pollTimer = window.setTimeout(async () => {
        await this.loadProgress(taskId, true);
      }, 3000);
    },
    async startBatch(taskId: string) {
      const task = useTaskContextStore().currentTask;
      const assessmentId = resolveAssessmentId(task);
      if (!assessmentId) {
        useUiStore().pushToast("当前任务缺少 assessmentId，暂时无法切换到真实阅卷主链路。", "risk");
        return;
      }

      this.loading = true;
      try {
        await gradingApi.start(assessmentId);
        useUiStore().pushToast("真实阅卷流程已启动，系统正在进入预处理阶段。");
        await this.loadProgress(taskId, true);
        await useTaskContextStore().loadTask(taskId);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "启动真实阅卷流程失败。";
        useUiStore().pushToast(message, "risk");
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async loadProgress(taskId: string, continuePolling = false) {
      const task = useTaskContextStore().currentTask;
      const assessmentId = resolveAssessmentId(task);
      this.progress = assessmentId ? mapProgress(taskId, await gradingApi.progress(assessmentId)) : await batchApi.progress(taskId);

      if (this.progress.status === "completed" || this.progress.status === "failed") {
        this.stopPolling();
      } else if (continuePolling && document.visibilityState === "visible") {
        this.schedulePoll(taskId);
      }

      await useTaskContextStore().loadTask(taskId);
    },
    async loadLogs(taskId: string) {
      this.logs = await batchApi.logs(taskId);
    },
    async loadResults(taskId: string) {
      this.loading = true;
      try {
        const task = useTaskContextStore().currentTask;
        const assessmentId = resolveAssessmentId(task);
        if (!assessmentId) {
          const [students, analytics] = await Promise.all([resultApi.students(taskId), resultApi.analytics(taskId)]);
          this.students = students;
          this.analytics = analytics;
          return;
        }

        const finalResults = await finalResultApi.list(assessmentId);
        this.students = finalResults.map((item) => mapFinalResultToStudentRow(assessmentId, item));
        this.analytics = buildAnalytics(this.students);
      } finally {
        this.loading = false;
      }
    },
    async loadStudent(studentId: string, taskId: string, submissionId?: string, finalResultId?: string) {
      this.loading = true;
      this.currentStudent = null;
      try {
        const task = useTaskContextStore().currentTask;
        const assessmentId = resolveAssessmentId(task);
        if (!assessmentId) {
          this.currentStudent = await resultApi.student(studentId, taskId);
          return;
        }

        const selectedRow =
          this.students.find((item) => item.submissionId === submissionId) ??
          this.students.find((item) => item.finalResultId === finalResultId) ??
          this.students.find((item) => item.id === studentId);

        if (!selectedRow?.submissionId) {
          throw new ApiError(400, "未找到 submissionId，暂时无法查询真实 score-items 详情。");
        }

        const scoreItems = await submissionApi.scoreItems(selectedRow.submissionId);
        this.currentStudent = mapScoreItemsToStudentDetail(assessmentId, selectedRow, scoreItems);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "未能加载学生评分详情。";
        useUiStore().pushToast(message, "risk");
      } finally {
        this.loading = false;
      }
    },
    async confirmCurrentStudent() {
      const detail = this.currentStudent;
      if (!detail?.finalResultId) {
        useUiStore().pushToast("当前详情缺少 finalResultId，无法确认成绩。", "risk");
        return;
      }

      const teacherId = resolveTeacherId(useAuthStore().user);
      if (!teacherId) {
        useUiStore().pushToast("当前登录用户缺少 teacherId，无法调用确认接口。", "risk");
        return;
      }

      this.loading = true;
      try {
        await finalResultApi.confirm(detail.finalResultId, teacherId);
        detail.reviewStatus = "CONFIRMED";
        detail.confirmedAt = new Date().toISOString();

        const row = this.students.find((item) => item.finalResultId === detail.finalResultId);
        if (row) {
          row.reviewStatus = "CONFIRMED";
          row.gateStatus = "CONFIRMED";
          row.confirmedAt = detail.confirmedAt;
          row.riskTags = row.riskTags.filter((tag) => tag !== "PENDING" && tag !== "ADJUSTED");
          if (!row.riskTags.includes("CONFIRMED")) {
            row.riskTags = ["CONFIRMED", ...row.riskTags];
          }
        }

        useUiStore().pushToast("教师确认已提交到真实后端接口。");
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "确认成绩失败。";
        useUiStore().pushToast(message, "risk");
      } finally {
        this.loading = false;
      }
    },
    async loadExports(taskId: string) {
      this.exports = await exportApi.history(taskId);
    },
    async createExport(taskId: string) {
      this.loading = true;
      try {
        const record = await exportApi.start(taskId);
        this.exports = [record, ...this.exports];
        useUiStore().pushToast("Excel 导出记录已生成。");
      } finally {
        this.loading = false;
      }
    },
  },
});
