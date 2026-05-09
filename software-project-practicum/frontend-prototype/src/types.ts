export type ConfigStatus = "draft" | "confirmed" | "in_use";
export type AnswerParseStatus = "uploading" | "parsing" | "parse_failed" | ConfigStatus;
export type WorkspaceStatus = "unchecked" | "valid" | "invalid" | "initializing";
export type BatchStatus = "idle" | "preprocessing" | "scoring" | "aggregating" | "completed" | "failed";
export type CourseStatus = "not_ready" | "idle" | "running" | "completed";
export type RubricSource = "manual" | "template_copy" | "text_generated" | "rubric_copy";
export type QualityFlag =
  | "low_confidence"
  | "traceability_gap"
  | "consistency_issue"
  | "placeholder_residue"
  | "gate_warning";

export type User = {
  id: string;
  name: string;
  username: string;
  teacherId?: string | number;
};

export type TaskSummary = {
  id: string;
  courseName: string;
  className: string;
  taskName: string;
  taskType: string;
  studentCount: number;
  submittedCount: number;
  configReady: boolean;
  configProgress: number;
  batchStatus: BatchStatus;
  nextAction: string;
};

export type TaskDetail = TaskSummary & {
  assessmentId?: string;
  templateId?: string | null;
  questionId?: string | null;
  courseCode: string;
  term: string;
  score: number;
  deadline: string;
  description: string;
  configStatuses: {
    answers: ConfigStatus | "missing";
    rubric: ConfigStatus | "missing";
    exportTemplate: ConfigStatus | "missing";
    workspace: WorkspaceStatus;
  };
};

export type CourseClassGroup = {
  className: string;
  studentCount: number;
  submittedCount: number;
  activeTaskCount: number;
  tasks: TaskDetail[];
};

export type TaskCourseGroup = {
  courseName: string;
  courseCode: string;
  term: string;
  status: CourseStatus;
  recentBatchSummary: string;
  classCount: number;
  totalStudents: number;
  taskCount: number;
  readyTaskCount: number;
  runningTaskCount: number;
  completedTaskCount: number;
  classes: CourseClassGroup[];
};

export type TaskClassGroup = CourseClassGroup;
export type CourseSummary = TaskCourseGroup;

export type CourseTaskGroup = {
  taskType: string;
  tasks: TaskDetail[];
};

export type ConfigBlocker = {
  id: string;
  title: string;
  detail: string;
};

export type AnswerVersion = {
  id: string;
  version: string;
  fileName: string;
  uploadedAt: string;
  parseStatus: AnswerParseStatus;
  itemCount: number;
  activatedAt?: string;
  status: ConfigStatus | "parse_failed";
  current: boolean;
  parseMessage?: string;
};

export type StandardAnswerRecord = {
  id: string | number;
  question_definition_id?: string | number;
  version_no?: number;
  answer_text?: string;
  answer_json?: string;
  status?: number | string;
  created_at?: string;
  updated_at?: string;
};

export type RubricDimension = {
  id: string;
  name: string;
  maxScore: number;
  description: string;
};

export type Rubric = {
  id: string;
  name: string;
  version: string;
  source: RubricSource;
  status: ConfigStatus;
  updatedAt: string;
  description: string;
  warnings: string[];
  totalScore: number;
  dimensions: RubricDimension[];
  yaml: string;
  createdAt?: string;
  copiedFromName?: string;
  lastUsedTaskName?: string;
  editCount?: number;
};

export type RubricDraft = {
  name: string;
  description: string;
  totalScore: number;
  dimensions: RubricDimension[];
  warnings: string[];
  yaml: string;
  canBind: boolean;
};

export type RubricCompileResponse = {
  rubricName: string;
  totalScore: number;
  dimensions: Array<{
    code: string;
    name: string;
    maxScore: number;
    description: string;
    evidenceRequirements: string[];
    levels: Array<{
      level: string;
      scoreRange: [number, number];
      description: string;
    }>;
    deductionRules: Array<{
      condition: string;
      deduct: number;
    }>;
  }>;
  capRules: Array<{
    condition: string;
    capScore: number;
    reason?: string;
  }>;
  reviewFlags: Array<{
    condition: string;
    action: string;
  }>;
  warnings: string[];
  canSave: boolean;
  rubricJson: Record<string, unknown>;
};

export type ExportSheet = {
  id: string;
  name: string;
  columns: Array<{ id: string; label: string; enabled: boolean }>;
};

export type ExportTemplate = {
  id: string;
  name: string;
  version: string;
  status: ConfigStatus;
  fileNameRule: string;
  updatedAt: string;
  sheets: ExportSheet[];
};

export type WorkspaceConfig = {
  rootPath: string;
  rawPath: string;
  irPath: string;
  scoresPath: string;
  reportsPath: string;
  status: WorkspaceStatus;
  lastCheckedAt?: string;
  lastMessage?: string;
};

export type SubmissionRecord = {
  id: string | number;
  assessment_id?: string | number;
  student_id?: string | number;
  source_submission_id?: string;
  submit_status?: string;
  submitted_at?: string;
};

export type SubmissionUploadResult = {
  submissionId?: string | number;
  assetId?: string | number;
  file?: string;
  rawWorkspace?: {
    synced?: boolean;
    path?: string;
    message?: string;
  };
};

export type ExportStartResult = {
  assessmentId?: string | number;
  scriptResult?: unknown;
  report?: string | null;
};

export type BatchProgress = {
  taskId: string;
  status: BatchStatus;
  startedAt?: string;
  updatedAt: string;
  total: number;
  completed: number;
  currentStepLabel: string;
  qualityFlags: Array<{ flag: QualityFlag; count: number; label: string }>;
};

export type RealGradingStatus = "QUEUED" | "PREPROCESSING" | "GRADING" | "COMPLETED" | "FAILED";

export type GradingProgressResponse = {
  assessmentId: string | number;
  status: RealGradingStatus;
  message?: string;
  scriptResult?: unknown;
  scriptProgress?: {
    total?: number;
    completed?: number;
    failed?: number;
    pending?: number;
    last_updated?: string;
    completed_ids?: string[];
    failed_ids?: Array<{ id?: string; error?: string }>;
    pending_ids?: string[];
  };
  scriptProgressStaleSeconds?: number;
  scriptProgressError?: string;
  importSummary?: {
    importedCount?: number;
    skippedCount?: number;
    failedCount?: number;
  };
  startedAt?: string;
  updatedAt?: string;
};

export type BatchLog = {
  time: string;
  level: "info" | "warn" | "error";
  message: string;
};

export type StudentRow = {
  id: string;
  assessmentId?: string;
  submissionId?: string;
  finalResultId?: string;
  studentId?: string;
  studentNumber: string;
  name: string;
  anonymousId: string;
  score: number;
  grade: string;
  confidence: number;
  gateStatus: string;
  reviewStatus?: string;
  confirmedAt?: string;
  traceabilityGapCount: number;
  consistencyIssueCount: number;
  riskTags: string[];
};

export type FinalResultRecord = {
  id: string | number;
  submissionId?: string | number;
  submission_id?: string | number;
  studentId?: string | number;
  student_id?: string | number;
  studentNo?: string;
  student_no?: string;
  studentName?: string;
  student_name?: string;
  finalScore?: number;
  final_score?: number;
  percentileScore?: number;
  percentile_score?: number;
  grade?: string;
  overallConfidence?: number;
  overall_confidence?: number;
  reviewStatus?: string;
  review_status?: string;
  confirmedAt?: string;
  confirmed_at?: string;
};

export type AnalysisSummary = {
  averageScore: number;
  totalStudents: number;
  lowConfidenceCount: number;
  gateWarningCount: number;
  placeholderResidueCount: number;
  scoreBands: Array<{ label: string; value: number }>;
  topIssues: Array<{ title: string; count: number; detail: string }>;
};

export type StudentDetail = {
  id: string;
  assessmentId?: string;
  submissionId?: string;
  finalResultId?: string;
  studentId?: string;
  name: string;
  studentNumber: string;
  anonymousId: string;
  score: number;
  percentileScore: number;
  grade: string;
  confidence: number;
  reviewStatus?: string;
  confirmedAt?: string;
  summary: string;
  qualityFindings: string[];
  dimensions: Array<{
    id: string;
    name: string;
    score: number;
    maxScore: number;
    confidence: number;
    evidence: string;
    reasoning: string;
    matched: string[];
    missing: string[];
    improvement: string;
  }>;
  traceability: {
    requirements: string[];
    hldCoverage: Array<{ requirement: string; status: "covered" | "weak" | "missing"; evidence: string }>;
    lldCoverage: Array<{ requirement: string; status: "covered" | "weak" | "missing"; evidence: string }>;
    uncoveredRequirements: string[];
  };
  gates: Array<{ name: string; passed: boolean; detail: string; onFail: string }>;
  materials: {
    documentCount: number;
    wordCount: number;
    imageCount: number;
    roles: string[];
    logs: string[];
  };
};

export type ScoreItemRecord = {
  id: string | number;
  criterionCode?: string;
  criterion_code?: string;
  criterionName?: string;
  criterion_name?: string;
  rubricDefinitionId?: string | number;
  rubric_definition_id?: string | number;
  score?: number;
  maxScore?: number;
  max_score?: number;
  confidence?: number;
  evidence?: string;
  evidenceText?: string;
  evidence_text?: string;
  evidenceJson?: string;
  evidence_json?: string;
  comment?: string;
  commentText?: string;
  comment_text?: string;
};

export type ExportRecord = {
  id: string;
  createdAt: string;
  fileName: string;
  templateVersion: string;
  status: "processing" | "completed" | "failed";
  warnings: string[];
};
