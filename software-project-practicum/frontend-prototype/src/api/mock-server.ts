import type {
  AnalysisSummary,
  AnswerVersion,
  BatchLog,
  BatchProgress,
  BatchStatus,
  ConfigBlocker,
  ConfigStatus,
  ExportRecord,
  ExportTemplate,
  QualityFlag,
  Rubric,
  RubricDraft,
  StudentDetail,
  StudentRow,
  TaskDetail,
  TaskSummary,
  User,
  WorkspaceConfig,
} from "../types";

type SessionRecord = { userId: string } | null;

type MockDatabase = {
  users: Array<User & { password: string }>;
  tasks: TaskDetail[];
  answers: Record<string, AnswerVersion[]>;
  rubrics: Rubric[];
  taskRubricBinding: Record<string, string>;
  templates: ExportTemplate[];
  taskTemplateBinding: Record<string, string>;
  workspaces: Record<string, WorkspaceConfig>;
  batches: Record<string, { status: BatchStatus; startedAt?: string; fail?: boolean }>;
  students: Record<string, StudentRow[]>;
  studentDetails: Record<string, StudentDetail>;
  analytics: Record<string, AnalysisSummary>;
  exports: Record<string, ExportRecord[]>;
};

const DB_KEY = "grader-mock-db-v2";
const SESSION_KEY = "grader-mock-session-v2";

const nowIso = () => new Date().toISOString();
const uid = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
const formatVersion = (count: number) => `v${count}.0`;

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const buildFallbackStudentDetail = (student: StudentRow): StudentDetail => ({
  id: student.id,
  name: student.name,
  studentNumber: student.studentNumber,
  anonymousId: student.anonymousId,
  score: student.score,
  percentileScore: student.score,
  grade: student.grade,
  confidence: student.confidence,
  summary: `${student.name} 的列表结果已生成，但尚未写入完整评分明细。系统基于结果列表生成临时解释，便于教师继续查看。`,
  qualityFindings: student.riskTags.length > 0 ? student.riskTags : ["当前样本暂无额外质量提示。"],
  dimensions: [
    {
      id: "fallback-overall",
      name: "综合表现",
      score: student.score,
      maxScore: 100,
      confidence: student.confidence,
      evidence: "该条解释由结果列表兜底生成，完整证据需等待后端评分详情文件补齐。",
      reasoning: `当前总分为 ${student.score}，等级为 ${student.grade}，置信度为 ${student.confidence}。`,
      matched: ["结果列表已有总分、等级和风险标签。"],
      missing: student.traceabilityGapCount > 0 ? [`存在 ${student.traceabilityGapCount} 个追踪缺口。`] : ["暂无明确缺失项。"],
      improvement: "建议补齐该学生的完整评分 JSON，以展示逐维度证据、推理和改进建议。",
    },
  ],
  traceability: {
    requirements: ["完整评分详情待补齐"],
    hldCoverage: [
      {
        requirement: "完整评分详情待补齐",
        status: student.traceabilityGapCount > 0 ? "weak" : "covered",
        evidence: "当前仅能从结果列表读取追踪缺口数量。",
      },
    ],
    lldCoverage: [
      {
        requirement: "完整评分详情待补齐",
        status: student.traceabilityGapCount > 0 ? "weak" : "covered",
        evidence: "当前仅能从结果列表读取追踪缺口数量。",
      },
    ],
    uncoveredRequirements: student.traceabilityGapCount > 0 ? ["完整追踪明细待补齐"] : [],
  },
  gates: [
    {
      name: "结果列表门禁状态",
      passed: student.gateStatus === "通过",
      detail: student.gateStatus,
      onFail: "flag",
    },
  ],
  materials: {
    documentCount: 0,
    wordCount: 0,
    imageCount: 0,
    roles: [],
    logs: ["完整材料摘要待后端评分详情补齐。"],
  },
});

const seedDatabase = (): MockDatabase => {
  const rubrics: Rubric[] = [
    {
      id: "rubric-traceability-1",
      name: "软件项目基础实践追踪式评分标准",
      version: "v1.2",
      source: "text_generated",
      status: "in_use",
      updatedAt: "2026-04-17 09:20",
      description: "强调需求-概设-详设追踪链、模板残留检查与一致性问题提示。",
      warnings: [],
      totalScore: 100,
      dimensions: [
        { id: "req-scope", name: "需求范围与核心用例清晰度", maxScore: 18, description: "关注需求目标、范围、角色和核心用例。" },
        { id: "trace", name: "需求-概设-详设追踪承接", maxScore: 24, description: "检查关键需求是否在后续设计中承接。" },
        { id: "consistency", name: "模板残留与术语一致性", maxScore: 12, description: "检查模板占位和跨章节术语不一致。" },
      ],
      yaml: "rubric_id: software-project-traceability-v1_2\ntotal_score: 100\n...",
    },
    {
      id: "rubric-common-1",
      name: "课程组通用文档评分标准",
      version: "v2.0",
      source: "template_copy",
      status: "confirmed",
      updatedAt: "2026-04-15 11:00",
      description: "适用于一般课程文档，不强调追踪链。",
      warnings: ["未包含追踪式门禁规则。"],
      totalScore: 100,
      dimensions: [
        { id: "structure", name: "结构完整性", maxScore: 30, description: "检查文档结构完整度。" },
        { id: "quality", name: "内容质量", maxScore: 70, description: "检查内容展开情况。" },
      ],
      yaml: "rubric_id: common-doc-v2_0\ntotal_score: 100\n...",
    },
  ];

  const templates: ExportTemplate[] = [
    {
      id: "template-main-1",
      name: "重邮课程阅卷结果表",
      version: "v1.0",
      status: "in_use",
      fileNameRule: "{课程名称}-{任务名称}-{日期}.xlsx",
      updatedAt: "2026-04-17 08:30",
      sheets: [
        {
          id: "summary",
          name: "成绩总表",
          columns: [
            { id: "studentNumber", label: "学号", enabled: true },
            { id: "name", label: "姓名", enabled: true },
            { id: "score", label: "总分", enabled: true },
            { id: "grade", label: "等级", enabled: true },
            { id: "comment", label: "评语", enabled: true },
          ],
        },
        {
          id: "analytics",
          name: "统计分析",
          columns: [
            { id: "avg", label: "平均分", enabled: true },
            { id: "bands", label: "分数段分布", enabled: true },
            { id: "issues", label: "高频问题", enabled: true },
          ],
        },
        {
          id: "details",
          name: "评分明细",
          columns: [
            { id: "student", label: "学生", enabled: true },
            { id: "dimension", label: "维度", enabled: true },
            { id: "evidence", label: "评分依据", enabled: true },
            { id: "confidence", label: "置信度", enabled: true },
          ],
        },
      ],
    },
  ];

  const tasks: TaskDetail[] = [
    {
      id: "exp3",
      courseName: "软件项目基础实践",
      className: "2024级软件工程 3 班",
      taskName: "实验三：需求规格说明书",
      taskType: "课程文档评分",
      studentCount: 48,
      submittedCount: 42,
      configReady: false,
      configProgress: 83,
      batchStatus: "idle",
      nextAction: "补齐评分标准与路径检测后开始阅卷",
      courseCode: "SE-EXP-2026",
      term: "2025-2026-2",
      score: 100,
      deadline: "2026-04-18 23:59",
      description: "评阅需求规格说明书并检查其与后续设计承接关系。",
      configStatuses: {
        answers: "in_use",
        rubric: "confirmed",
        exportTemplate: "in_use",
        workspace: "unchecked",
      },
    },
    {
      id: "exp4",
      courseName: "软件项目基础实践",
      className: "2024级软件工程 4 班",
      taskName: "实验四：概要设计说明书",
      taskType: "课程文档评分",
      studentCount: 46,
      submittedCount: 31,
      configReady: true,
      configProgress: 100,
      batchStatus: "completed",
      nextAction: "查看结果分析并导出",
      courseCode: "SE-EXP-2026",
      term: "2025-2026-2",
      score: 100,
      deadline: "2026-04-28 23:59",
      description: "评阅概要设计说明书，检查模块设计与需求适配性。",
      configStatuses: {
        answers: "in_use",
        rubric: "in_use",
        exportTemplate: "in_use",
        workspace: "valid",
      },
    },
    {
      id: "frontier-report",
      courseName: "软件前沿技术",
      className: "2024级软件工程1班",
      taskName: "作业一：前沿技术调研报告",
      taskType: "课程作业",
      studentCount: 74,
      submittedCount: 68,
      configReady: true,
      configProgress: 100,
      batchStatus: "idle",
      nextAction: "可直接开始阅卷并在结果完成后导出",
      courseCode: "FE-2026",
      term: "2025-2026-2",
      score: 100,
      deadline: "2026-04-22 23:59",
      description: "面向软件前沿技术调研报告的摘要、结构与论证评分。",
      configStatuses: {
        answers: "in_use",
        rubric: "in_use",
        exportTemplate: "in_use",
        workspace: "valid",
      },
    },
    {
      id: "frontier-quiz",
      courseName: "软件前沿技术",
      className: "2024级软件工程2班",
      taskName: "期中测验：前沿工具与框架",
      taskType: "课程考试",
      studentCount: 70,
      submittedCount: 70,
      configReady: true,
      configProgress: 100,
      batchStatus: "completed",
      nextAction: "查看评分分布并导出成绩",
      courseCode: "FE-2026",
      term: "2025-2026-2",
      score: 100,
      deadline: "2026-04-10 21:00",
      description: "用于评估学生对前沿工具与框架的理解和综合应用。",
      configStatuses: {
        answers: "in_use",
        rubric: "in_use",
        exportTemplate: "in_use",
        workspace: "valid",
      },
    },
    {
      id: "testing-exam",
      courseName: "软件测试",
      className: "2023级软件工程2班",
      taskName: "阶段考试：测试用例设计",
      taskType: "课程考试",
      studentCount: 52,
      submittedCount: 52,
      configReady: false,
      configProgress: 66,
      batchStatus: "idle",
      nextAction: "先补齐标准答案和路径配置，再开始评分",
      courseCode: "TEST-2026",
      term: "2025-2026-2",
      score: 100,
      deadline: "2026-04-25 18:00",
      description: "重点评估测试用例设计完整性、边界场景和缺陷预估能力。",
      configStatuses: {
        answers: "confirmed",
        rubric: "confirmed",
        exportTemplate: "in_use",
        workspace: "unchecked",
      },
    },
  ];

  const answers: Record<string, AnswerVersion[]> = {
    exp3: [
      {
        id: "ans-exp3-1",
        version: "v1.2",
        fileName: "需求规格说明书标准答案.docx",
        uploadedAt: "2026-04-16 20:40",
        parseStatus: "in_use",
        itemCount: 12,
        activatedAt: "2026-04-17 08:45",
        status: "in_use",
        current: true,
      },
      {
        id: "ans-exp3-2",
        version: "v1.3",
        fileName: "需求规格说明书标准答案-修订.docx",
        uploadedAt: "2026-04-17 09:55",
        parseStatus: "draft",
        itemCount: 14,
        status: "draft",
        current: false,
      },
    ],
    exp4: [
      {
        id: "ans-exp4-1",
        version: "v1.0",
        fileName: "概要设计标准答案.pdf",
        uploadedAt: "2026-04-12 19:30",
        parseStatus: "in_use",
        itemCount: 10,
        activatedAt: "2026-04-12 20:05",
        status: "in_use",
        current: true,
      },
    ],
    "frontier-report": [
      {
        id: "ans-frontier-report-1",
        version: "v1.0",
        fileName: "前沿技术调研报告标准答案.docx",
        uploadedAt: "2026-04-15 20:10",
        parseStatus: "in_use",
        itemCount: 8,
        activatedAt: "2026-04-16 09:20",
        status: "in_use",
        current: true,
      },
    ],
    "frontier-quiz": [
      {
        id: "ans-frontier-quiz-1",
        version: "v1.0",
        fileName: "前沿工具期中测验标准答案.pdf",
        uploadedAt: "2026-04-09 18:00",
        parseStatus: "in_use",
        itemCount: 6,
        activatedAt: "2026-04-09 18:20",
        status: "in_use",
        current: true,
      },
    ],
    "testing-exam": [
      {
        id: "ans-testing-exam-1",
        version: "v0.9",
        fileName: "测试用例设计考试答案.docx",
        uploadedAt: "2026-04-13 21:00",
        parseStatus: "confirmed",
        itemCount: 9,
        activatedAt: "2026-04-13 21:30",
        status: "confirmed",
        current: true,
      },
    ],
  };

  const workspaces: Record<string, WorkspaceConfig> = {
    exp3: {
      rootPath: "workspace/2025-2026-2/软件项目基础实践/实验三",
      rawPath: "workspace/2025-2026-2/软件项目基础实践/实验三/raw",
      irPath: "workspace/2025-2026-2/软件项目基础实践/实验三/ir",
      scoresPath: "workspace/2025-2026-2/软件项目基础实践/实验三/scores",
      reportsPath: "workspace/2025-2026-2/软件项目基础实践/实验三/reports",
      status: "unchecked",
    },
    exp4: {
      rootPath: "workspace/2025-2026-2/软件项目基础实践/实验四",
      rawPath: "workspace/2025-2026-2/软件项目基础实践/实验四/raw",
      irPath: "workspace/2025-2026-2/软件项目基础实践/实验四/ir",
      scoresPath: "workspace/2025-2026-2/软件项目基础实践/实验四/scores",
      reportsPath: "workspace/2025-2026-2/软件项目基础实践/实验四/reports",
      status: "valid",
      lastCheckedAt: "2026-04-17 08:10",
      lastMessage: "目录结构完整，可用于批量阅卷。",
    },
    "frontier-report": {
      rootPath: "workspace/2025-2026-2/软件前沿技术/作业一",
      rawPath: "workspace/2025-2026-2/软件前沿技术/作业一/raw",
      irPath: "workspace/2025-2026-2/软件前沿技术/作业一/ir",
      scoresPath: "workspace/2025-2026-2/软件前沿技术/作业一/scores",
      reportsPath: "workspace/2025-2026-2/软件前沿技术/作业一/reports",
      status: "valid",
      lastCheckedAt: "2026-04-17 09:00",
      lastMessage: "目录结构完整，已准备好开始阅卷。",
    },
    "frontier-quiz": {
      rootPath: "workspace/2025-2026-2/软件前沿技术/期中测验",
      rawPath: "workspace/2025-2026-2/软件前沿技术/期中测验/raw",
      irPath: "workspace/2025-2026-2/软件前沿技术/期中测验/ir",
      scoresPath: "workspace/2025-2026-2/软件前沿技术/期中测验/scores",
      reportsPath: "workspace/2025-2026-2/软件前沿技术/期中测验/reports",
      status: "valid",
      lastCheckedAt: "2026-04-12 08:40",
      lastMessage: "期中测验已完成阅卷，可用于结果回看。",
    },
    "testing-exam": {
      rootPath: "workspace/2025-2026-2/软件测试/阶段考试",
      rawPath: "workspace/2025-2026-2/软件测试/阶段考试/raw",
      irPath: "workspace/2025-2026-2/软件测试/阶段考试/ir",
      scoresPath: "workspace/2025-2026-2/软件测试/阶段考试/scores",
      reportsPath: "workspace/2025-2026-2/软件测试/阶段考试/reports",
      status: "unchecked",
    },
  };

  const studentsExp3: StudentRow[] = [
    {
      id: "anon-001",
      studentNumber: "2019214047",
      name: "谢雨晨",
      anonymousId: "anon-001",
      score: 78,
      grade: "通过",
      confidence: 0.84,
      gateStatus: "通过",
      traceabilityGapCount: 1,
      consistencyIssueCount: 1,
      riskTags: ["结构较完整"],
    },
    {
      id: "anon-002",
      studentNumber: "2024214281",
      name: "宋玲芸",
      anonymousId: "anon-002",
      score: 83,
      grade: "通过",
      confidence: 0.91,
      gateStatus: "通过",
      traceabilityGapCount: 0,
      consistencyIssueCount: 1,
      riskTags: ["可直接导出"],
    },
    {
      id: "anon-003",
      studentNumber: "2024214306",
      name: "吴锐",
      anonymousId: "anon-003",
      score: 74,
      grade: "建议关注",
      confidence: 0.78,
      gateStatus: "通过",
      traceabilityGapCount: 3,
      consistencyIssueCount: 3,
      riskTags: ["低置信度", "追踪缺失"],
    },
  ];

  const detailExp3: StudentDetail = {
    id: "anon-003",
    name: "吴锐",
    studentNumber: "2024214306",
    anonymousId: "anon-003",
    score: 72,
    percentileScore: 74,
    grade: "建议关注",
    confidence: 0.78,
    summary: "需求阶段较完整，但“薪资结算进度跟踪”未在概要设计与详细设计中承接。",
    qualityFindings: ["模板章节仍有残留。", "概要设计中的模块承接关系不够完整。", "关键需求缺少后续接口或页面承接。"],
    dimensions: [
      {
        id: "req-scope",
        name: "需求范围与核心用例清晰度",
        score: 5,
        maxScore: 8,
        confidence: 0.91,
        evidence: "需求目标、角色和主要功能具备基础展开。",
        reasoning: "需求主体较完整，但关键业务边界和异常流展开不足。",
        matched: ["主要角色明确", "核心业务流程可读"],
        missing: ["异常流说明不足"],
        improvement: "建议为关键用例补充前置条件、异常流和约束。",
      },
      {
        id: "trace",
        name: "需求-概设-详设追踪承接",
        score: 5,
        maxScore: 8,
        confidence: 0.9,
        evidence: "概设中能找到注册、搜索、报名等承接，但缺少薪资结算进度跟踪。",
        reasoning: "多数需求有承接链，但关键缺失降低整体追踪得分。",
        matched: ["注册登录已承接", "岗位搜索已承接"],
        missing: ["薪资结算进度跟踪", "实名认证承接不足"],
        improvement: "补充需求-模块-页面-接口映射表，显式承接关键需求。",
      },
      {
        id: "consistency",
        name: "模板残留与术语一致性",
        score: 3,
        maxScore: 6,
        confidence: 0.82,
        evidence: "部分类设计仍保留跨项目模板语句。",
        reasoning: "模板残留削弱结果可信度，应作为质量提示。",
        matched: ["章节结构基本完整"],
        missing: ["模板占位未清理"],
        improvement: "统一术语并删除模板占位内容。",
      },
    ],
    traceability: {
      requirements: [
        "岗位发布、搜索报名、审核录用、双方评价的全流程线上化",
        "薪资结算进度跟踪",
        "企业资质与岗位审核",
      ],
      hldCoverage: [
        { requirement: "岗位发布、搜索报名、审核录用、双方评价的全流程线上化", status: "covered", evidence: "概要设计 4.1-4.7 均有说明。" },
        { requirement: "薪资结算进度跟踪", status: "missing", evidence: "未找到对应模块、页面或接口设计。" },
      ],
      lldCoverage: [
        { requirement: "岗位发布、搜索报名、审核录用、双方评价的全流程线上化", status: "weak", evidence: "存在部分页面与类设计，但链路不完整。" },
        { requirement: "薪资结算进度跟踪", status: "missing", evidence: "详细设计中未找到页面、类或接口。" },
      ],
      uncoveredRequirements: ["薪资结算进度跟踪", "实名认证承接不足"],
    },
    gates: [
      { name: "需求文档存在性", passed: true, detail: "requirements present", onFail: "flag" },
      { name: "概要设计文档存在性", passed: true, detail: "hld present", onFail: "flag" },
      { name: "详细设计文档存在性", passed: true, detail: "lld present", onFail: "flag" },
    ],
    materials: {
      documentCount: 3,
      wordCount: 17368,
      imageCount: 14,
      roles: ["requirements", "hld", "lld"],
      logs: ["学生目录识别成功，生成 anon-003。", "成功抽取 3 份文档文本内容。", "识别到需求、概设、详设三类文档角色。"],
    },
  };

  return {
    users: [{ id: "teacher-001", name: "王老师", username: "teacher", password: "123456" }],
    tasks,
    answers,
    rubrics,
    taskRubricBinding: {
      exp3: "rubric-traceability-1",
      exp4: "rubric-traceability-1",
      "frontier-report": "rubric-common-1",
      "frontier-quiz": "rubric-common-1",
      "testing-exam": "rubric-common-1",
    },
    templates,
    taskTemplateBinding: {
      exp3: "template-main-1",
      exp4: "template-main-1",
      "frontier-report": "template-main-1",
      "frontier-quiz": "template-main-1",
      "testing-exam": "template-main-1",
    },
    workspaces,
    batches: {
      exp3: { status: "idle" },
      exp4: { status: "completed", startedAt: "2026-04-16T08:20:00.000Z" },
      "frontier-report": { status: "idle" },
      "frontier-quiz": { status: "completed", startedAt: "2026-04-11T09:00:00.000Z" },
      "testing-exam": { status: "idle" },
    },
    students: {
      exp3: studentsExp3,
      exp4: studentsExp3.map((student, index) => ({ ...student, id: `exp4-${student.id}`, anonymousId: `exp4-${student.anonymousId}`, score: student.score + index })),
      "frontier-report": studentsExp3.map((student, index) => ({
        ...student,
        id: `frontier-report-${student.id}`,
        anonymousId: `frontier-report-${student.anonymousId}`,
        score: student.score + 5 + index,
      })),
      "frontier-quiz": studentsExp3.map((student, index) => ({
        ...student,
        id: `frontier-quiz-${student.id}`,
        anonymousId: `frontier-quiz-${student.anonymousId}`,
        score: student.score + 8 + index,
      })),
      "testing-exam": studentsExp3.map((student, index) => ({
        ...student,
        id: `testing-exam-${student.id}`,
        anonymousId: `testing-exam-${student.anonymousId}`,
        score: student.score - 2 + index,
      })),
    },
    studentDetails: {
      "anon-003": detailExp3,
      "exp4-anon-003": { ...detailExp3, id: "exp4-anon-003", anonymousId: "exp4-anon-003", score: 81, percentileScore: 82, confidence: 0.87 },
      "frontier-report-anon-003": {
        ...detailExp3,
        id: "frontier-report-anon-003",
        anonymousId: "frontier-report-anon-003",
        score: 86,
        percentileScore: 88,
        confidence: 0.9,
        summary: "调研报告结构完整，技术选择有根据，仍可补强落地性分析。",
      },
      "frontier-quiz-anon-003": {
        ...detailExp3,
        id: "frontier-quiz-anon-003",
        anonymousId: "frontier-quiz-anon-003",
        score: 89,
        percentileScore: 91,
        confidence: 0.93,
        summary: "对前沿工具链理解较完整，关键概念表述清晰，可直接纳入课程结果分析。",
      },
      "testing-exam-anon-003": {
        ...detailExp3,
        id: "testing-exam-anon-003",
        anonymousId: "testing-exam-anon-003",
        score: 69,
        percentileScore: 71,
        confidence: 0.8,
        summary: "测试用例覆盖主流程，但边界场景和异常路径设计仍有明显缺口。",
      },
    },
    analytics: {
      exp3: {
        averageScore: 74.3,
        totalStudents: 48,
        lowConfidenceCount: 4,
        gateWarningCount: 3,
        placeholderResidueCount: 2,
        scoreBands: [
          { label: "60-69", value: 6 },
          { label: "70-79", value: 18 },
          { label: "80-89", value: 16 },
          { label: "90+", value: 4 },
        ],
        topIssues: [
          { title: "薪资结算进度跟踪未覆盖", count: 8, detail: "关键需求没有在后续设计中承接。" },
          { title: "用例规约展开不足", count: 6, detail: "异常流、约束说明不足。" },
          { title: "模板占位残留", count: 2, detail: "仍保留模板提示语。" },
        ],
      },
      exp4: {
        averageScore: 79.4,
        totalStudents: 46,
        lowConfidenceCount: 2,
        gateWarningCount: 1,
        placeholderResidueCount: 1,
        scoreBands: [
          { label: "60-69", value: 3 },
          { label: "70-79", value: 14 },
          { label: "80-89", value: 19 },
          { label: "90+", value: 6 },
        ],
        topIssues: [
          { title: "模块边界说明不足", count: 5, detail: "部分模块设计边界不够清楚。" },
        ],
      },
      "frontier-report": {
        averageScore: 82.6,
        totalStudents: 74,
        lowConfidenceCount: 2,
        gateWarningCount: 1,
        placeholderResidueCount: 0,
        scoreBands: [
          { label: "60-69", value: 4 },
          { label: "70-79", value: 18 },
          { label: "80-89", value: 28 },
          { label: "90+", value: 12 },
        ],
        topIssues: [
          { title: "技术路线论证不充分", count: 7, detail: "结论有，但缺少对技术选型依据的展开。" },
          { title: "参考资料引用格式不统一", count: 4, detail: "存在引用来源不完整或格式不一致的问题。" },
        ],
      },
      "frontier-quiz": {
        averageScore: 85.1,
        totalStudents: 70,
        lowConfidenceCount: 1,
        gateWarningCount: 0,
        placeholderResidueCount: 0,
        scoreBands: [
          { label: "60-69", value: 2 },
          { label: "70-79", value: 14 },
          { label: "80-89", value: 32 },
          { label: "90+", value: 15 },
        ],
        topIssues: [
          { title: "框架适用场景判断偏弱", count: 5, detail: "能说出工具名称，但落到使用场景时不够准确。" },
        ],
      },
      "testing-exam": {
        averageScore: 73.8,
        totalStudents: 52,
        lowConfidenceCount: 3,
        gateWarningCount: 2,
        placeholderResidueCount: 1,
        scoreBands: [
          { label: "60-69", value: 8 },
          { label: "70-79", value: 21 },
          { label: "80-89", value: 14 },
          { label: "90+", value: 3 },
        ],
        topIssues: [
          { title: "边界用例覆盖不足", count: 9, detail: "主流程覆盖基本具备，但边界和异常场景遗漏较多。" },
          { title: "断言设计不够具体", count: 6, detail: "存在“测试通过”但缺少明确判定标准的情况。" },
        ],
      },
    },
    exports: {
      exp3: [
        {
          id: "export-1",
          createdAt: "2026-04-16 18:05",
          fileName: "软件项目基础实践-实验三-预览版.xlsx",
          templateVersion: "v1.0",
          status: "completed",
          warnings: ["4 份低置信度样本", "2 份模板残留样本"],
        },
      ],
      exp4: [],
      "frontier-report": [],
      "frontier-quiz": [
        {
          id: "export-frontier-quiz-1",
          createdAt: "2026-04-12 18:30",
          fileName: "软件前沿技术-期中测验-2026-04-12.xlsx",
          templateVersion: "v1.0",
          status: "completed",
          warnings: ["1 份低置信度样本"],
        },
      ],
      "testing-exam": [],
    },
  };
};

const readDb = (): MockDatabase => {
  const raw = window.localStorage.getItem(DB_KEY);
  if (!raw) {
    const seeded = seedDatabase();
    window.localStorage.setItem(DB_KEY, JSON.stringify(seeded));
    return seeded;
  }
  return JSON.parse(raw) as MockDatabase;
};

const writeDb = (db: MockDatabase) => {
  window.localStorage.setItem(DB_KEY, JSON.stringify(db));
};

const readSession = (): SessionRecord => {
  const raw = window.localStorage.getItem(SESSION_KEY);
  return raw ? (JSON.parse(raw) as SessionRecord) : null;
};

const writeSession = (session: SessionRecord) => {
  if (session) {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    window.localStorage.removeItem(SESSION_KEY);
  }
};

const delay = async (ms = 400) => new Promise((resolve) => window.setTimeout(resolve, ms));

const unauthorized = () => new Response(JSON.stringify({ message: "未登录或会话已失效。" }), { status: 401 });
const ok = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const badRequest = (message: string) => new Response(JSON.stringify({ message }), { status: 400 });
const notFound = (message = "资源不存在。") => new Response(JSON.stringify({ message }), { status: 404 });

const ensureAuth = (): User | null => {
  const session = readSession();
  if (!session) return null;
  const db = readDb();
  const user = db.users.find((item) => item.id === session.userId);
  return user ? { id: user.id, name: user.name, username: user.username } : null;
};

const deriveBatchProgress = (taskId: string, db: MockDatabase): BatchProgress => {
  const task = db.tasks.find((item) => item.id === taskId);
  const batch = db.batches[taskId];
  const total = task?.submittedCount ?? 0;
  const qualityFlags: Array<{ flag: QualityFlag; count: number; label: string }> = [
    { flag: "low_confidence", count: 4, label: "低置信度" },
    { flag: "placeholder_residue", count: 2, label: "模板残留" },
    { flag: "gate_warning", count: 3, label: "门禁异常" },
  ];

  if (!batch || batch.status === "idle") {
    return {
      taskId,
      status: "idle",
      updatedAt: nowIso(),
      total,
      completed: 0,
      currentStepLabel: "等待开始阅卷",
      qualityFlags,
    };
  }

  const startedAt = batch.startedAt ? new Date(batch.startedAt).getTime() : Date.now();
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  if (batch.status === "preprocessing" && elapsedSeconds >= 3) {
    batch.status = "scoring";
  }
  if (batch.status === "scoring") {
    const completed = Math.min(total, Math.floor(Math.max(0, elapsedSeconds - 3) * 2));
    if (completed >= total) {
      batch.status = "aggregating";
    }
  }
  if (batch.status === "aggregating" && elapsedSeconds >= Math.max(8, total / 2)) {
    batch.status = "completed";
    const taskIndex = db.tasks.findIndex((item) => item.id === taskId);
    if (taskIndex >= 0) {
      db.tasks[taskIndex].batchStatus = "completed";
      db.tasks[taskIndex].nextAction = "查看结果分析并导出 Excel";
    }
    writeDb(db);
  }

  let currentStepLabel = "等待开始阅卷";
  let completed = 0;
  if (batch.status === "preprocessing") {
    currentStepLabel = "预处理中：抽取文本与识别文档角色";
  } else if (batch.status === "scoring") {
    completed = Math.min(total, Math.floor(Math.max(0, elapsedSeconds - 3) * 2));
    currentStepLabel = "评分中：基于 Rubric 执行模型评分";
  } else if (batch.status === "aggregating") {
    completed = total;
    currentStepLabel = "汇总中：聚合统计与导出数据";
  } else if (batch.status === "completed") {
    completed = total;
    currentStepLabel = "已完成：可以查看结果分析和导出";
  } else if (batch.status === "failed") {
    currentStepLabel = "执行失败：请查看日志摘要";
  }

  return {
    taskId,
    status: batch.status,
    startedAt: batch.startedAt,
    updatedAt: nowIso(),
    total,
    completed,
    currentStepLabel,
    qualityFlags,
  };
};

const deriveTask = (taskId: string, db: MockDatabase): TaskDetail | undefined => {
  const task = db.tasks.find((item) => item.id === taskId);
  if (!task) return undefined;
  const rubricId = db.taskRubricBinding[taskId];
  const rubric = db.rubrics.find((item) => item.id === rubricId);
  const answers = db.answers[taskId] ?? [];
  const templateId = db.taskTemplateBinding[taskId];
  const template = db.templates.find((item) => item.id === templateId);
  const workspace = db.workspaces[taskId];

  const configStatuses = {
    answers: answers.find((item) => item.current)?.status ?? "missing",
    rubric: rubric?.status ?? "missing",
    exportTemplate: template?.status ?? "missing",
    workspace: workspace?.status ?? "unchecked",
  } satisfies TaskDetail["configStatuses"];

  const configReady =
    (configStatuses.answers === "confirmed" || configStatuses.answers === "in_use") &&
    (configStatuses.rubric === "confirmed" || configStatuses.rubric === "in_use") &&
    (configStatuses.exportTemplate === "confirmed" || configStatuses.exportTemplate === "in_use") &&
    configStatuses.workspace === "valid";

  const configProgress =
    [
      configStatuses.answers !== "missing",
      configStatuses.rubric !== "missing",
      configStatuses.exportTemplate !== "missing",
      configStatuses.workspace !== "unchecked",
      configStatuses.workspace === "valid",
      answers.some((item) => item.current),
    ].filter(Boolean).length *
    16;

  return { ...task, configReady, configProgress: Math.min(100, configProgress), configStatuses };
};

const getConfigBlockers = (taskId: string, db: MockDatabase): ConfigBlocker[] => {
  const task = deriveTask(taskId, db);
  if (!task) return [];
  const blockers: ConfigBlocker[] = [];
  if (!(task.configStatuses.answers === "confirmed" || task.configStatuses.answers === "in_use")) {
    blockers.push({ id: "answers", title: "标准答案未激活", detail: "当前任务还没有可用的标准答案版本。" });
  }
  if (!(task.configStatuses.rubric === "confirmed" || task.configStatuses.rubric === "in_use")) {
    blockers.push({ id: "rubric", title: "评分标准未确认", detail: "请先确认评分标准或绑定使用中的版本。" });
  }
  if (!(task.configStatuses.exportTemplate === "confirmed" || task.configStatuses.exportTemplate === "in_use")) {
    blockers.push({ id: "template", title: "Excel 模板未确认", detail: "当前任务还没有已确认的结果表格式模板。" });
  }
  if (task.configStatuses.workspace !== "valid") {
    blockers.push({ id: "workspace", title: "路径检测未通过", detail: "请先检测工作区路径或初始化目录结构。" });
  }
  return blockers;
};

const normalizeDateTime = (value: string) =>
  new Date(value).toLocaleString("zh-CN", { hour12: false }).replace(/\//g, "-");

const activateAnswerVersion = (taskId: string, versionId: string, db: MockDatabase) => {
  const versions = db.answers[taskId] ?? [];
  versions.forEach((item) => {
    if (item.id === versionId) {
      item.current = true;
      item.status = "in_use";
      item.parseStatus = "in_use";
      item.activatedAt = normalizeDateTime(nowIso());
    } else if (item.current) {
      item.current = false;
      item.status = "confirmed";
      item.parseStatus = "confirmed";
    }
  });
};

const updateAnswerLifecycle = (db: MockDatabase) => {
  Object.values(db.answers).forEach((versions) => {
    versions.forEach((item) => {
      if (item.parseStatus === "parsing" && item.parseMessage && item.parseMessage.startsWith("ready:")) {
        const readyAt = Number(item.parseMessage.slice(6));
        if (Date.now() >= readyAt) {
          item.itemCount = 14;
          item.parseStatus = "draft";
          item.status = "draft";
          item.parseMessage = undefined;
        }
      }
    });
  });
};

const levelFromFlag = (flag: QualityFlag): BatchLog["level"] => {
  if (flag === "gate_warning") return "warn";
  if (flag === "placeholder_residue") return "warn";
  return "info";
};

export const mockFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  await delay(250);
  const requestUrl = new URL(typeof input === "string" ? input : input.toString(), window.location.origin);
  const method = (init?.method ?? "GET").toUpperCase();
  const pathname = requestUrl.pathname;
  const db = readDb();
  updateAnswerLifecycle(db);
  writeDb(db);

  if (pathname === "/api/auth/login" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { username?: string; password?: string };
    const user = db.users.find((item) => item.username === body.username && item.password === body.password);
    if (!user) return badRequest("用户名或密码错误。");
    writeSession({ userId: user.id });
    return ok({ id: user.id, name: user.name, username: user.username });
  }

  if (pathname === "/api/auth/me" && method === "GET") {
    const user = ensureAuth();
    return user ? ok(user) : unauthorized();
  }

  if (pathname === "/api/auth/logout" && method === "POST") {
    writeSession(null);
    return ok({ success: true });
  }

  const user = ensureAuth();
  if (!user) return unauthorized();

  if (pathname === "/api/tasks" && method === "GET") {
    const tasks = db.tasks.map((item) => deriveTask(item.id, db)).filter(Boolean) as TaskDetail[];
    return ok(tasks);
  }

  const taskMatch = pathname.match(/^\/api\/tasks\/([^/]+)$/);
  if (taskMatch && method === "GET") {
    const task = deriveTask(taskMatch[1], db);
    return task ? ok(task) : notFound("任务不存在。");
  }

  const configStatusMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/config-status$/);
  if (configStatusMatch && method === "GET") {
    return ok({ blockers: getConfigBlockers(configStatusMatch[1], db) });
  }

  const answersMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/answers$/);
  if (answersMatch && method === "GET") {
    return ok(db.answers[answersMatch[1]] ?? []);
  }

  if (answersMatch && method === "POST") {
    const taskId = answersMatch[1];
    const form = init?.body as FormData;
    const file = form?.get("file");
    if (!(file instanceof File)) return badRequest("未选择标准答案文件。");
    const versions = db.answers[taskId] ?? [];
    const shouldFail = file.name.toLowerCase().includes("fail");
    const answer: AnswerVersion = {
      id: uid("ans"),
      version: formatVersion(versions.length + 1),
      fileName: file.name,
      uploadedAt: normalizeDateTime(nowIso()),
      parseStatus: shouldFail ? "parse_failed" : "parsing",
      itemCount: 0,
      status: shouldFail ? "parse_failed" : "draft",
      current: false,
      parseMessage: shouldFail ? "文件解析失败，请检查格式或内容。" : `ready:${Date.now() + 1400}`,
    };
    db.answers[taskId] = [answer, ...versions];
    writeDb(db);
    return ok(answer, 201);
  }

  const answerVersionMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/answers\/([^/]+)$/);
  if (answerVersionMatch && method === "GET") {
    const [_, taskId, versionId] = answerVersionMatch;
    const version = (db.answers[taskId] ?? []).find((item) => item.id === versionId);
    return version ? ok(version) : notFound("标准答案版本不存在。");
  }

  const answerActivateMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/answers\/([^/]+)\/activate$/);
  if (answerActivateMatch && method === "POST") {
    const [_, taskId, versionId] = answerActivateMatch;
    activateAnswerVersion(taskId, versionId, db);
    writeDb(db);
    return ok({ success: true });
  }

  if (pathname === "/api/rubrics" && method === "GET") {
    return ok(db.rubrics);
  }

  if (pathname === "/api/rubrics" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as Rubric;
    const rubric: Rubric = {
      ...body,
      id: uid("rubric"),
      createdAt: body.createdAt ?? normalizeDateTime(nowIso()),
      updatedAt: normalizeDateTime(nowIso()),
    };
    db.rubrics.unshift(rubric);
    writeDb(db);
    return ok(rubric, 201);
  }

  const rubricUpdateMatch = pathname.match(/^\/api\/rubrics\/([^/]+)$/);
  if (rubricUpdateMatch && method === "PUT") {
    const id = rubricUpdateMatch[1];
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as Partial<Rubric>;
    const rubric = db.rubrics.find((item) => item.id === id);
    if (!rubric) return notFound("评分标准不存在。");
    Object.assign(rubric, body, { updatedAt: normalizeDateTime(nowIso()) });
    writeDb(db);
    return ok(rubric);
  }

  if (rubricUpdateMatch && method === "DELETE") {
    const id = rubricUpdateMatch[1];
    const rubric = db.rubrics.find((item) => item.id === id);
    if (!rubric) return notFound("评分标准不存在。");
    const boundTask = Object.values(db.taskRubricBinding).some((rubricId) => rubricId === id);
    const deletable = rubric.source === "rubric_copy" && rubric.status === "draft" && !boundTask;
    if (!deletable) return badRequest("当前仅允许删除未绑定任务的草稿副本。");
    db.rubrics = db.rubrics.filter((item) => item.id !== id);
    writeDb(db);
    return ok({ success: true });
  }

  if (pathname === "/api/rubrics/generate" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { prompt?: string };
    const hasMissingGate = !(body.prompt ?? "").includes("门禁");
    const totalScore = body.prompt?.includes("100") ? 100 : 96;
    const draft: RubricDraft = {
      name: "文本生成 Rubric 初稿",
      description: "基于教师自然语言描述生成的结构化评分标准草稿。",
      totalScore,
      dimensions: [
        { id: "req-scope", name: "需求范围与核心用例清晰度", maxScore: 18, description: "关注需求目标、范围与主要用例。" },
        { id: "trace", name: "需求-概设-详设追踪承接", maxScore: 24, description: "检查关键需求是否在后续设计中承接。" },
        { id: "consistency", name: "模板残留与术语一致性", maxScore: 12, description: "检查模板残留和术语不一致。" },
      ],
      warnings: [
        "当前识别出的维度总分未闭合到 100 分。",
        ...(hasMissingGate ? ["未识别到明确的门禁规则定义。"] : []),
      ],
      yaml: `rubric_id: generated-draft\ntotal_score: ${totalScore}\n...`,
      canBind: !hasMissingGate && totalScore === 100,
    };
    return ok(draft);
  }

  const bindingMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/rubric-binding$/);
  if (bindingMatch && method === "GET") {
    const rubric = db.rubrics.find((item) => item.id === db.taskRubricBinding[bindingMatch[1]]);
    return rubric ? ok(rubric) : notFound("当前任务未绑定评分标准。");
  }

  if (bindingMatch && method === "POST") {
    const taskId = bindingMatch[1];
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { rubricId: string };
    db.taskRubricBinding[taskId] = body.rubricId;
    const rubric = db.rubrics.find((item) => item.id === body.rubricId);
    if (rubric && (rubric.status === "confirmed" || rubric.status === "draft")) {
      rubric.status = "in_use";
    }
    writeDb(db);
    return ok({ success: true });
  }

  if (pathname === "/api/export-templates" && method === "GET") {
    return ok(db.templates);
  }

  if (pathname === "/api/export-templates" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as ExportTemplate;
    const template: ExportTemplate = {
      ...body,
      id: uid("template"),
      updatedAt: normalizeDateTime(nowIso()),
    };
    db.templates.unshift(template);
    writeDb(db);
    return ok(template, 201);
  }

  const templateUpdateMatch = pathname.match(/^\/api\/export-templates\/([^/]+)$/);
  if (templateUpdateMatch && method === "PUT") {
    const template = db.templates.find((item) => item.id === templateUpdateMatch[1]);
    if (!template) return notFound("Excel 模板不存在。");
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as Partial<ExportTemplate>;
    Object.assign(template, body, { updatedAt: normalizeDateTime(nowIso()) });
    writeDb(db);
    return ok(template);
  }

  const taskTemplateMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/export-template$/);
  if (taskTemplateMatch && method === "GET") {
    const template = db.templates.find((item) => item.id === db.taskTemplateBinding[taskTemplateMatch[1]]);
    return template ? ok(template) : notFound("当前任务未绑定 Excel 模板。");
  }

  const taskTemplateBindMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/export-template\/bind$/);
  if (taskTemplateBindMatch && method === "POST") {
    const taskId = taskTemplateBindMatch[1];
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { templateId: string };
    db.taskTemplateBinding[taskId] = body.templateId;
    const template = db.templates.find((item) => item.id === body.templateId);
    if (template && template.status === "confirmed") {
      template.status = "in_use";
    }
    writeDb(db);
    return ok({ success: true });
  }

  const workspaceMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/workspace$/);
  if (workspaceMatch && method === "GET") {
    const workspace = db.workspaces[workspaceMatch[1]];
    return workspace ? ok(workspace) : notFound("未找到工作区配置。");
  }

  const workspaceCheckMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/workspace\/check$/);
  if (workspaceCheckMatch && method === "POST") {
    const workspace = db.workspaces[workspaceCheckMatch[1]];
    if (!workspace) return notFound("未找到工作区配置。");
    workspace.lastCheckedAt = normalizeDateTime(nowIso());
    if (workspace.rootPath.toLowerCase().includes("invalid")) {
      workspace.status = "invalid";
      workspace.lastMessage = "工作区路径不可用，请检查根路径或权限。";
    } else {
      workspace.status = "valid";
      workspace.lastMessage = "目录结构完整，可用于批量阅卷。";
    }
    writeDb(db);
    return ok(workspace);
  }

  const workspaceInitMatch = pathname.match(/^\/api\/tasks\/([^/]+)\/workspace\/init$/);
  if (workspaceInitMatch && method === "POST") {
    const workspace = db.workspaces[workspaceInitMatch[1]];
    if (!workspace) return notFound("未找到工作区配置。");
    workspace.status = "initializing";
    workspace.lastCheckedAt = normalizeDateTime(nowIso());
    workspace.lastMessage = "正在初始化目录结构...";
    writeDb(db);
    await delay(700);
    const nextDb = readDb();
    nextDb.workspaces[workspaceInitMatch[1]].status = "valid";
    nextDb.workspaces[workspaceInitMatch[1]].lastCheckedAt = normalizeDateTime(nowIso());
    nextDb.workspaces[workspaceInitMatch[1]].lastMessage = "目录初始化成功，建议重新检测确认。";
    writeDb(nextDb);
    return ok(nextDb.workspaces[workspaceInitMatch[1]]);
  }

  if (pathname === "/api/batch/start" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { taskId: string };
    const blockers = getConfigBlockers(body.taskId, db);
    if (blockers.length > 0) return badRequest("当前任务配置未完成，不能开始阅卷。");
    db.batches[body.taskId] = { status: "preprocessing", startedAt: nowIso() };
    const task = db.tasks.find((item) => item.id === body.taskId);
    if (task) {
      task.batchStatus = "preprocessing";
      task.nextAction = "等待系统完成自动阅卷";
    }
    writeDb(db);
    return ok({ success: true });
  }

  if (pathname === "/api/batch/progress" && method === "GET") {
    const taskId = requestUrl.searchParams.get("taskId");
    if (!taskId) return badRequest("缺少 taskId。");
    const nextDb = readDb();
    const progress = deriveBatchProgress(taskId, nextDb);
    const task = nextDb.tasks.find((item) => item.id === taskId);
    if (task) {
      task.batchStatus = progress.status;
    }
    writeDb(nextDb);
    return ok(progress);
  }

  if (pathname === "/api/batch/logs" && method === "GET") {
    const taskId = requestUrl.searchParams.get("taskId");
    if (!taskId) return badRequest("缺少 taskId。");
    const progress = deriveBatchProgress(taskId, db);
    const logs: BatchLog[] = [
      { time: normalizeDateTime(nowIso()), level: "info", message: `当前阶段：${progress.currentStepLabel}` },
      ...progress.qualityFlags.map((item) => ({
        time: normalizeDateTime(nowIso()),
        level: levelFromFlag(item.flag),
        message: `${item.label}样本 ${item.count} 份`,
      })),
    ];
    return ok(logs);
  }

  if (pathname === "/api/students" && method === "GET") {
    const taskId = requestUrl.searchParams.get("taskId");
    if (!taskId) return badRequest("缺少 taskId。");
    return ok(db.students[taskId] ?? []);
  }

  const studentMatch = pathname.match(/^\/api\/students\/([^/]+)$/);
  if (studentMatch && method === "GET") {
    const studentId = decodeURIComponent(studentMatch[1]);
    const taskId = requestUrl.searchParams.get("taskId") ?? "";
    const fallbackId = taskId && studentId.startsWith(`${taskId}-`) ? studentId.slice(taskId.length + 1) : studentId;
    const row = taskId
      ? db.students[taskId]?.find((student) => student.id === studentId || student.anonymousId === studentId || student.id === fallbackId || student.anonymousId === fallbackId)
      : undefined;
    const detail = db.studentDetails[studentId] ?? db.studentDetails[fallbackId] ?? (row ? buildFallbackStudentDetail(row) : null);
    return detail ? ok(detail) : notFound("未找到该学生的评分详情。");
  }

  if (pathname === "/api/analytics" && method === "GET") {
    const taskId = requestUrl.searchParams.get("taskId");
    if (!taskId) return badRequest("缺少 taskId。");
    return ok(db.analytics[taskId]);
  }

  if (pathname === "/api/batch/export" && method === "POST") {
    const body = JSON.parse((init?.body as string | undefined) ?? "{}") as { taskId: string };
    const task = deriveTask(body.taskId, db);
    const template = db.templates.find((item) => item.id === db.taskTemplateBinding[body.taskId]);
    if (!task || !template) return badRequest("当前任务缺少导出模板。");
    const record: ExportRecord = {
      id: uid("export"),
      createdAt: normalizeDateTime(nowIso()),
      fileName: `${task.courseName}-${task.taskName}-${new Date().toISOString().slice(0, 10)}.xlsx`,
      templateVersion: template.version,
      status: "completed",
      warnings: ["4 份低置信度样本", "2 份模板残留样本", "3 份门禁异常样本"],
    };
    db.exports[body.taskId] = [record, ...(db.exports[body.taskId] ?? [])];
    writeDb(db);
    return ok(record, 201);
  }

  if (pathname === "/api/exports" && method === "GET") {
    const taskId = requestUrl.searchParams.get("taskId");
    if (!taskId) return badRequest("缺少 taskId。");
    return ok(db.exports[taskId] ?? []);
  }

  return notFound("未实现的模拟接口。");
};
