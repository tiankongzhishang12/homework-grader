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
import {
  canonicalReviewStatus,
  hasLowConfidence,
  isAdjustedStatus,
  isConfirmedStatus,
  isPendingConfirmation,
  isReviewRequired,
  reviewStatusLabel,
} from "../utils/review-status";
import { useAuthStore } from "./auth";
import { useTaskContextStore } from "./task-context";
import { useUiStore } from "./ui";

let pollTimer: number | null = null;

type ScoreItemEvidencePayload = {
  criterion_name?: string;
  reasoning?: string;
  improvement?: string;
  missing_points?: string[];
  matched_core_points?: string[];
};

const toText = (value: unknown, fallback = "") => (value === null || value === undefined ? fallback : String(value));

const toNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const toOptionalNumber = (value: unknown) => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const parseEvidenceJson = (raw: unknown): ScoreItemEvidencePayload | null => {
  if (!raw || typeof raw !== "string") return null;
  try {
    const parsed = JSON.parse(raw) as ScoreItemEvidencePayload;
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
};

const isNumericId = (value: string | null | undefined) => Boolean(value && /^\d+$/.test(value));

const resolveAssessmentId = (task: TaskDetail | null) => {
  if (!task) return null;
  if (isNumericId(task.assessmentId)) return task.assessmentId as string;
  // Temporary fallback only for legacy task payloads that still omit assessmentId.
  // If task.id is a prototype route id like "answer-card-demo", we must not call real assessment APIs with it.
  if (isNumericId(task.id)) return task.id;
  return null;
};

const ensureAssessmentId = (task: TaskDetail | null) => {
  const assessmentId = resolveAssessmentId(task);
  if (assessmentId) return assessmentId;
  throw new ApiError(400, "当前任务缺少真实 assessmentId。");
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
  const scriptProgress = progress.scriptProgress;
  if (progress.status === "GRADING" && scriptProgress) {
    const completed = toNumber(scriptProgress.completed);
    const failed = toNumber(scriptProgress.failed);
    const pending = toNumber(scriptProgress.pending);
    const total = toNumber(scriptProgress.total);
    const staleSeconds = toNumber(progress.scriptProgressStaleSeconds);
    const staleText = staleSeconds > 180 ? ` 进度已 ${staleSeconds} 秒未更新，模型请求可能停滞。` : "";
    return `大模型评分中：已完成 ${completed} 份，失败 ${failed} 份，待处理 ${pending} 份，共 ${total} 份。${staleText}`;
  }
  if (progress.scriptProgressError) return `阅卷正在运行，但暂时无法读取脚本进度：${progress.scriptProgressError}`;
  if (progress.message) return translateProgressMessage(progress.message);
  switch (progress.status) {
    case "QUEUED":
      return "任务已进入队列，等待预处理。";
    case "PREPROCESSING":
      return "正在预处理学生提交文件。";
    case "GRADING":
      return "正在进行大模型评分和结果导入。";
    case "COMPLETED":
      return "阅卷完成，评分结果已导入。";
    case "FAILED":
      return "阅卷失败，请查看技术日志。";
    default:
      return "等待开始阅卷。";
  }
};

const translateProgressMessage = (message: string) => {
  const map: Record<string, string> = {
    "Grading task queued.": "阅卷任务已进入队列。",
    "Running submission preprocessing.": "正在预处理学生提交文件。",
    "Running automatic grading.": "正在进行大模型评分。",
    "Grading completed and all results imported.": "阅卷完成，评分结果已导入。",
    "Automatic grading failed.": "自动阅卷失败。",
    "Submission preprocessing failed.": "学生文件预处理失败。",
  };
  return map[message] ?? message;
};

const fallbackQualitySummary = (progress: GradingProgressResponse) => {
  const summary = progress.importSummary ?? {};
  const scriptProgress = progress.scriptProgress;
  const importSkippedCount = toNumber(summary.skippedCount);
  const importFailedCount = toNumber(summary.failedCount);
  const scriptFailedCount = toNumber(scriptProgress?.failed);
  const progressStalled = toNumber(progress.scriptProgressStaleSeconds) > 180;
  return {
    totalIssues: importSkippedCount + importFailedCount + scriptFailedCount + (progressStalled ? 1 : 0),
    importSkippedCount,
    importFailedCount,
    scriptFailedCount,
    progressStalled,
    needsReviewCount: 0,
    lowConfidenceCount: 0,
  };
};

const fallbackExecutionSteps = (progress: GradingProgressResponse): BatchProgress["executionSteps"] => {
  const status = mapRealStatusToBatchStatus(progress.status);
  const runtimeRubric = progress.runtimeRubric;
  const gradingRunning = status === "scoring";
  const completed = status === "completed";
  const failed = status === "failed";
  return [
    { key: "preflight", label: "配置检查", status: status === "idle" ? "pending" : "completed", detail: "已完成基础配置检查" },
    { key: "workspace", label: "工作区准备", status: status === "idle" ? "pending" : "completed", detail: "已准备学生提交工作区" },
    {
      key: "runtime_rubric",
      label: "评分标准加载",
      status: runtimeRubric ? "completed" : failed ? "failed" : status === "preprocessing" ? "running" : "pending",
      detail: runtimeRubric ? `已使用 ${runtimeRubric.rubricRuntimeId}` : "开始阅卷后将加载已保存评分标准",
    },
    { key: "preprocess", label: "学生文件预处理", status: status === "preprocessing" ? "running" : completed || gradingRunning ? "completed" : failed ? "failed" : "pending", detail: "生成评分所需中间材料" },
    { key: "grading", label: "大模型评分", status: gradingRunning ? "running" : completed ? "completed" : failed ? "failed" : "pending", detail: toStepLabel(progress) },
    { key: "import", label: "结果导入", status: completed ? "completed" : failed && progress.importSummary ? "failed" : "pending", detail: "导入评分结果到系统" },
  ];
};

const mapProgress = (taskId: string, progress: GradingProgressResponse): BatchProgress => {
  const summary = progress.importSummary ?? {};
  const scriptProgress = progress.scriptProgress;
  const imported = toNumber(summary.importedCount);
  const skipped = toNumber(summary.skippedCount);
  const failed = toNumber(summary.failedCount);
  const scriptCompleted = toNumber(scriptProgress?.completed);
  const scriptFailed = toNumber(scriptProgress?.failed);
  const scriptTotal = toNumber(scriptProgress?.total);
  const qualityFlags: BatchProgress["qualityFlags"] = [];
  if (skipped > 0) qualityFlags.push({ flag: "traceability_gap", count: skipped, label: "缁撴灉瀵煎叆璺宠繃" });
  if (failed > 0) qualityFlags.push({ flag: "gate_warning", count: failed, label: "缁撴灉瀵煎叆澶辫触" });
  if (scriptFailed > 0) qualityFlags.push({ flag: "gate_warning", count: scriptFailed, label: "璇勫垎澶辫触" });
  if (toNumber(progress.scriptProgressStaleSeconds) > 180) qualityFlags.push({ flag: "gate_warning", count: 1, label: "杩涘害鍋滄粸" });

  return {
    taskId,
    status: mapRealStatusToBatchStatus(progress.status),
    gradingMode: progress.gradingMode,
    startedAt: progress.startedAt,
    updatedAt: progress.updatedAt ?? new Date().toISOString(),
    total: scriptProgress ? scriptTotal : imported + skipped + failed,
    completed: scriptProgress ? scriptCompleted : imported,
    currentStepLabel: toStepLabel(progress),
    qualityFlags,
    runtimeRubric: progress.runtimeRubric,
    executionSteps: progress.executionSteps ?? fallbackExecutionSteps(progress),
    qualitySummary: progress.qualitySummary ?? fallbackQualitySummary(progress),
    workspaceSummary: progress.workspaceSummary,
  };
};

const mapFinalResultToStudentRow = (assessmentId: string, row: FinalResultRecord): StudentRow => {
  const studentId = toText(row.studentId ?? row.student_id, "");
  const submissionId = toText(row.submissionId ?? row.submission_id, "");
  const finalResultId = toText(row.id);
  const reviewStatus = canonicalReviewStatus(toText(row.reviewStatus ?? row.review_status, "AI_GENERATED"));
  const studentName = toText(row.studentName ?? row.student_name, "");
  const studentNo = toText(row.studentNo ?? row.student_no, "");
  const confidence = toOptionalNumber(row.overallConfidence ?? row.overall_confidence);
  const score = toNumber(row.finalScore ?? row.final_score);

  return {
    id: studentId || submissionId || finalResultId,
    assessmentId,
    submissionId,
    finalResultId,
    studentId,
    studentNumber: studentNo || "学号缺失",
    name: studentName || "未知学生",
    anonymousId: submissionId || finalResultId || studentId || "-",
    score,
    grade: toText(row.grade, "-"),
    confidence,
    gateStatus: reviewStatus,
    reviewStatus,
    confirmedAt: toText(row.confirmedAt ?? row.confirmed_at, ""),
    traceabilityGapCount: null,
    consistencyIssueCount: isAdjustedStatus(reviewStatus) ? 1 : 0,
    riskTags: [
      reviewStatusLabel(reviewStatus),
      ...(isPendingConfirmation(reviewStatus) ? ["待确认"] : []),
      ...(hasLowConfidence(confidence) ? ["低置信度"] : []),
    ],
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
      reviewRequiredCount: 0,
      gateWarningCount: 0,
      placeholderResidueCount: 0,
      scoreBands: emptyBands,
      topIssues: [],
    };
  }

  const averageScore = Number((students.reduce((sum, item) => sum + item.score, 0) / students.length).toFixed(1));
  const lowConfidenceCount = students.filter((item) => hasLowConfidence(item.confidence)).length;
  const reviewRequiredCount = students.filter((item) => isReviewRequired(item.reviewStatus) || isPendingConfirmation(item.reviewStatus)).length;
  const reviewStatusCount = new Map<string, number>();
  students.forEach((item) => {
    const key = canonicalReviewStatus(item.reviewStatus);
    reviewStatusCount.set(key, (reviewStatusCount.get(key) ?? 0) + 1);
  });

  return {
    averageScore,
    totalStudents: students.length,
    lowConfidenceCount,
    reviewRequiredCount,
    gateWarningCount: reviewRequiredCount,
    placeholderResidueCount: 0,
    scoreBands: [
      { label: "<60", value: students.filter((item) => item.score < 60).length },
      { label: "60-69", value: students.filter((item) => item.score >= 60 && item.score < 70).length },
      { label: "70-79", value: students.filter((item) => item.score >= 70 && item.score < 80).length },
      { label: "80-89", value: students.filter((item) => item.score >= 80 && item.score < 90).length },
      { label: "90+", value: students.filter((item) => item.score >= 90).length },
    ],
    topIssues: [...reviewStatusCount.entries()].map(([title, count]) => ({
      title: reviewStatusLabel(title),
      count,
      detail: `${count} 名学生当前处于${reviewStatusLabel(title)}状态。`,
    })),
  };
};

const normalizeEvidence = (item: ScoreItemRecord) => {
  const evidenceJsonText = item.evidenceJson ?? item.evidence_json;
  if (item.evidenceText) return item.evidenceText;
  if (item.evidence_text) return item.evidence_text;
  if (item.evidence) return item.evidence;
  if (evidenceJsonText) return toText(evidenceJsonText);
  return "当前评分项暂未返回评分证据。";
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
  summary: "该学生当前成绩已生成，请结合评分项明细和复核状态进行确认。",
  qualityFindings: [
    `当前复核状态：${reviewStatusLabel(student.reviewStatus)}`,
    `系统评分：${student.score} 分`,
    ...(isReviewRequired(student.reviewStatus) || isPendingConfirmation(student.reviewStatus)
      ? ["当前成绩尚未完成教师确认。"]
      : ["当前成绩已完成确认或发布。"]),
  ],
  dimensions: scoreItems.map((item, index) => {
    const evidenceJson = parseEvidenceJson(item.evidenceJson ?? item.evidence_json);
    return {
      id: toText(item.criterionCode ?? item.criterion_code ?? item.id, `score-item-${index + 1}`),
      name: toText(evidenceJson?.criterion_name ?? item.criterionName ?? item.criterion_name ?? item.id, `Score Item ${index + 1}`),
      score: toNumber(item.score),
      maxScore: toNumber(item.maxScore ?? item.max_score),
      confidence: toOptionalNumber(item.confidence),
      evidence: normalizeEvidence(item),
      reasoning: toText(evidenceJson?.reasoning ?? item.commentText ?? item.comment_text ?? item.comment, "当前评分项暂未返回评语。"),
      matched: Array.isArray(evidenceJson?.matched_core_points) ? evidenceJson.matched_core_points : [],
      missing: Array.isArray(evidenceJson?.missing_points) ? evidenceJson.missing_points : [],
      improvement: toText(evidenceJson?.improvement, "当前评分项暂未返回改进建议。"),
    };
  }),
  traceability: {
    requirements: [],
    hldCoverage: [],
    lldCoverage: [],
    uncoveredRequirements: [],
  },
  gates: [
    {
      name: "复核状态",
      passed: isConfirmedStatus(student.reviewStatus) || isAdjustedStatus(student.reviewStatus),
      detail: `当前状态：${reviewStatusLabel(student.reviewStatus)}`,
      onFail: "建议操作：教师确认或调整后再发布成绩。",
    },
  ],
  materials: {
    documentCount: 0,
    wordCount: 0,
    imageCount: 0,
    roles: [],
    logs: [],
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
    refreshingProgress: false,
    refreshingLogs: false,
    lastProgressRefreshedAt: null as string | null,
    lastLogsRefreshedAt: null as string | null,
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
    async startBatch(taskId: string, mode: "INCREMENTAL" | "FULL" = "INCREMENTAL") {
      this.loading = true;
      try {
        const assessmentId = ensureAssessmentId(useTaskContextStore().currentTask);
        await gradingApi.start(assessmentId, mode);
        useUiStore().pushToast(mode === "FULL" ? "已启动全量重新阅卷。" : "已启动增量阅卷。");
        await this.loadProgress(taskId, true);
        await this.loadLogs(taskId);
        await useTaskContextStore().loadTask(taskId);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "启动自动阅卷失败。";
        useUiStore().pushToast(message, "risk");
        if (error instanceof ApiError) {
          throw error;
        }
      } finally {
        this.loading = false;
      }
    },
    async loadProgress(taskId: string, continuePolling = false) {
      this.refreshingProgress = true;
      try {
        const task = useTaskContextStore().currentTask;
        const assessmentId = resolveAssessmentId(task);
        this.progress = assessmentId ? mapProgress(taskId, await gradingApi.progress(assessmentId)) : await batchApi.progress(taskId);
        this.lastProgressRefreshedAt = new Date().toISOString();
        if (assessmentId) {
          this.logs = await gradingApi.logs(assessmentId);
          this.lastLogsRefreshedAt = new Date().toISOString();
        }

        if (this.progress.status === "completed" || this.progress.status === "failed") {
          this.stopPolling();
        } else if (continuePolling && document.visibilityState === "visible") {
          this.schedulePoll(taskId);
        }

        await useTaskContextStore().loadTask(taskId);
      } finally {
        this.refreshingProgress = false;
      }
    },
    async loadLogs(taskId: string) {
      this.refreshingLogs = true;
      try {
        const task = useTaskContextStore().currentTask;
        const assessmentId = resolveAssessmentId(task);
        this.logs = assessmentId ? await gradingApi.logs(assessmentId) : await batchApi.logs(taskId);
        this.lastLogsRefreshedAt = new Date().toISOString();
      } finally {
        this.refreshingLogs = false;
      }
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
          throw new ApiError(400, "Current student row is missing submissionId.");
        }

        const scoreItems = await submissionApi.scoreItems(selectedRow.submissionId);
        this.currentStudent = mapScoreItemsToStudentDetail(assessmentId, selectedRow, scoreItems);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Failed to load student detail.";
        useUiStore().pushToast(message, "risk");
      } finally {
        this.loading = false;
      }
    },
    async confirmCurrentStudent() {
      const detail = this.currentStudent;
      if (!detail?.finalResultId) {
        useUiStore().pushToast("Current student detail is missing finalResultId.", "risk");
        return;
      }
      if (isConfirmedStatus(detail.reviewStatus)) {
        return;
      }

      const teacherId = resolveTeacherId(useAuthStore().user);
      if (!teacherId) {
        useUiStore().pushToast("Current login user is missing teacherId.", "risk");
        return;
      }

      this.loading = true;
      try {
        await finalResultApi.confirm(detail.finalResultId, teacherId);
        const taskStore = useTaskContextStore();
        const taskId = taskStore.currentTask?.id;
        if (taskId) {
          await this.loadResults(taskId);
          await this.loadStudent(detail.id, taskId, detail.submissionId, detail.finalResultId);
        }
        useUiStore().pushToast("Teacher confirmation submitted.");
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Failed to confirm final result.";
        useUiStore().pushToast(message, "risk");
      } finally {
        this.loading = false;
      }
    },
    async loadExports(taskId: string) {
      // Legacy demo export path: GET /api/exports?taskId=...
      // The formal export center now uses gradeExportApi through configStore.
      this.exports = await exportApi.history(taskId);
    },
    async createExport(taskId: string) {
      // Legacy demo export path: POST /api/batch/export.
      // Keep for compatibility until a dedicated export store replaces it.
      this.loading = true;
      try {
        const record = await exportApi.start(taskId);
        this.exports = [record, ...this.exports];
        useUiStore().pushToast("Export record created.");
      } finally {
        this.loading = false;
      }
    },
  },
});
