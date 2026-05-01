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

export type BatchLog = {
  time: string;
  level: "info" | "warn" | "error";
  message: string;
};

export type StudentRow = {
  id: string;
  studentNumber: string;
  name: string;
  anonymousId: string;
  score: number;
  grade: string;
  confidence: number;
  gateStatus: string;
  traceabilityGapCount: number;
  consistencyIssueCount: number;
  riskTags: string[];
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
  name: string;
  studentNumber: string;
  anonymousId: string;
  score: number;
  percentileScore: number;
  grade: string;
  confidence: number;
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

export type ExportRecord = {
  id: string;
  createdAt: string;
  fileName: string;
  templateVersion: string;
  status: "processing" | "completed" | "failed";
  warnings: string[];
};
