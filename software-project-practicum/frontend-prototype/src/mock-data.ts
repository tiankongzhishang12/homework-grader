export const primaryNav = [
  { label: "任务中心", to: "/tasks" },
  { label: "批量阅卷", to: "/grading" },
  { label: "结果分析", to: "/analysis" },
  { label: "导出中心", to: "/export" },
] as const;

export const taskOverview = {
  course: "软件项目基础实践",
  className: "2024级软件工程 3 班",
  taskName: "实验三：需求规格说明书",
  taskType: "课程文档评分",
  submitted: "42 / 48",
  readiness: "6 / 7 已就绪",
};

export const taskStats = [
  { label: "配置完成度", value: "86%", tone: "good" },
  { label: "已提交人数", value: "42", tone: "neutral" },
  { label: "待补配置项", value: "1", tone: "warn" },
  { label: "当前评分标准", value: "v1.2", tone: "neutral" },
] as const;

export const taskModules = [
  {
    title: "教学班级与学生名单",
    status: "已确认",
    owner: "学在重邮同步",
    version: "2026-04-17 09:10",
    summary: "班级、学号、姓名与提交名单已同步，可直接用于批量阅卷任务绑定。",
    actions: ["查看名单", "刷新同步"],
  },
  {
    title: "课程任务信息",
    status: "已确认",
    owner: "课程任务中心",
    version: "实验三 · 平时作业",
    summary: "任务名称、截止时间、满分与文档类型已绑定到当前班级。",
    actions: ["查看任务", "调整范围"],
  },
  {
    title: "标准答案",
    status: "已确认",
    owner: "教师上传模板",
    version: "v1.2",
    summary: "已抽取参考要求、关键点与术语规范，可为评语与命中点生成提供依据。",
    actions: ["查看版本", "上传更新"],
  },
  {
    title: "评分标准配置",
    status: "待补充",
    owner: "文本生成 + 人工确认",
    version: "草稿 v0.9",
    summary: "当前 Rubric 主体已生成，但仍需补齐门禁规则与总分闭合校验。",
    actions: ["进入标准库", "文本生成 Rubric"],
  },
  {
    title: "Excel 模板",
    status: "已确认",
    owner: "课程组模板",
    version: "导出模板 v1.0",
    summary: "成绩总表、统计分析、评分明细三张工作表结构已锁定。",
    actions: ["预览模板", "复制模板"],
  },
  {
    title: "批量路径配置",
    status: "已确认",
    owner: "系统默认规则",
    version: "workspace/2025-2026-2/软件项目基础实践/实验三",
    summary: "工作区目录已初始化，Python 与 Spring Boot 读写路径一致。",
    actions: ["检测路径", "查看日志"],
  },
] as const;

export const taskChecklist = [
  "评分标准配置是当前唯一未完全确认的模块，已生成草稿但仍需补齐门禁规则。",
  "开始阅卷前应确认任务满分、Rubric 总分与导出模板列结构保持一致。",
  "所有配置模块都应保留版本号与最后更新时间，方便结果回溯。",
] as const;

export const rubricLibraryStats = [
  { label: "评分标准总数", value: "6", tone: "neutral" },
  { label: "当前任务可用", value: "3", tone: "good" },
  { label: "文本生成来源", value: "2", tone: "warn" },
  { label: "使用中版本", value: "v1.2", tone: "good" },
] as const;

export const rubricLibrary = [
  {
    name: "软件项目基础实践追踪式评分标准",
    version: "v1.2",
    source: "文本生成后人工确认",
    status: "使用中",
    scope: "需求规格说明书 / 概要设计 / 详细设计",
    summary: "强调需求-概设-详设追踪链、缺失承接与模板残留检查。",
  },
  {
    name: "课程组通用文档评分标准",
    version: "v2.0",
    source: "模板复制",
    status: "已确认",
    scope: "课程报告 / 设计文档",
    summary: "适合一般课程文档评分，未针对追踪分析做强化。",
  },
  {
    name: "主观题分点评分标准",
    version: "v1.0",
    source: "手工创建",
    status: "草稿",
    scope: "简答题 / 论述题",
    summary: "以关键点与等级锚点为核心，适用于题目式阅卷任务。",
  },
] as const;

export const rubricFlowNotes = [
  "当前任务可直接从评分标准库选择已有版本，也可通过自然语言重新生成 Rubric 初稿。",
  "文本生成结果默认进入草稿态，只有补齐结构冲突与分值问题后才允许绑定到任务。",
  "评分标准详情中应保留来源、版本、生成时间和最近一次人工确认时间。",
] as const;

export const generatorContext = {
  course: "软件项目基础实践",
  taskName: "实验三：需求规格说明书",
  taskType: "课程文档评分",
  totalScore: "100 分",
  scope: "三文档联合追踪评分",
};

export const generatorTemplates = [
  "文档追踪式评分示例",
  "主观题分点评分示例",
  "课程报告评分示例",
] as const;

export const generatorPrompt = `请按需求规格说明书、概要设计说明书和详细设计说明书的承接关系评分。重点看需求是否清楚、概设是否覆盖需求、详设是否继续承接，并检查模板残留、术语不一致、关键模块缺失等问题。总分 100 分，要求生成维度评分、扣分点、门禁规则和评语要求。`;

export const generatorOptions = [
  { label: "生成模式", value: "严格模式" },
  { label: "Rubric 类型", value: "追踪评分" },
  { label: "输出细度", value: "维度 + 扣分点 + 门禁规则" },
  { label: "评语要求", value: "标准" },
] as const;

export const generatorSummary = [
  { label: "识别维度", value: "6 个", tone: "good" },
  { label: "总分闭合", value: "98 / 100", tone: "warn" },
  { label: "门禁规则", value: "3 条", tone: "good" },
  { label: "结构冲突", value: "1 处", tone: "risk" },
] as const;

export const generatedRubricCards = [
  {
    title: "需求范围与核心用例清晰度",
    score: "18 分",
    rule: "关注目标、范围、角色、核心用例与业务边界是否清楚。",
    deductions: ["核心需求未闭环扣 4-6 分", "用例命名空泛扣 2-3 分"],
  },
  {
    title: "需求-概设-详设追踪承接",
    score: "24 分",
    rule: "重点检查需求是否在概设和详设中均有明确承接。",
    deductions: ["关键需求未在后续设计中承接扣 6-10 分", "只出现文字提及但无设计展开扣 3-5 分"],
  },
  {
    title: "模板残留与术语一致性",
    score: "12 分",
    rule: "检查模板占位文本、跨项目术语残留与章节对象不一致问题。",
    deductions: ["出现模板残留直接标记风险", "核心模块名称前后不一致扣 2-4 分"],
  },
] as const;

export const generatedYaml = `rubric_id: software-project-traceability-v0_9
title: 软件项目基础实践追踪式评分标准
total_score: 100
dimensions:
  - id: req_scope
    name: 需求范围与核心用例清晰度
    max_score: 18
  - id: traceability_chain
    name: 需求-概设-详设追踪承接
    max_score: 24
gates:
  - id: requirements_present
    on_fail: flag
  - id: hld_present
    on_fail: flag
comment_rules:
  language: zh-CN
  tone: 建设性、具体、可追踪`;

export const generatorWarnings = [
  "输入中要求总分 100 分，但当前识别出的维度总分只有 98 分，建议补齐 2 分的分值归属。",
  "“模板残留直接判风险”已识别为规则，但尚未明确对应 on_fail 动作，建议补充为 warn 或 flag。",
  "评语要求已识别为建设性输出，但未识别长度约束，建议补充字数范围。",
] as const;

export const generatorMappings = [
  "输入提到“检查需求是否被后续设计承接”，已映射为 traceability_chain 维度。",
  "输入提到“模板残留、术语不一致”，已映射为一致性与模板残留规则。",
  "输入提到“生成门禁规则和评语要求”，已识别出 gates 与 comment_rules，但仍有细节待补充。",
] as const;

export const gradingStats = [
  { label: "当前阶段", value: "评分中", tone: "warn" },
  { label: "已识别文件", value: "126", tone: "good" },
  { label: "已完成评分", value: "39 / 48", tone: "good" },
  { label: "质量提示", value: "7", tone: "risk" },
] as const;

export const gradingSteps = [
  { name: "文件获取", status: "已完成", detail: "42 份提交已落盘，6 份缺失等待老师补交。" },
  { name: "预处理", status: "已完成", detail: "已生成 IR、student-mapping 与日志摘要。" },
  { name: "评分执行", status: "进行中", detail: "39 份已完成，剩余 9 份正在调用模型评分。" },
  { name: "结果汇总", status: "待开始", detail: "将在全部评分完成后聚合统计与导出数据。" },
  { name: "导出准备", status: "待开始", detail: "需等待结果汇总和模板字段检查完成。" },
] as const;

export const gradingAlerts = [
  { title: "文件缺失", detail: "6 名学生未检测到完整三类文档，系统已记录为质量提示。", tone: "warn" },
  { title: "低置信度样本", detail: "4 份样本置信度低于 0.80，建议后续在结果分析中抽查典型解释页。", tone: "risk" },
  { title: "模板残留", detail: "2 份样本识别到模板占位内容，已写入风险标签。", tone: "warn" },
] as const;

export const gradingRows = [
  {
    id: "anon-001",
    studentNumber: "2019214047",
    name: "谢雨晨",
    stage: "已完成",
    docs: "3 份文档",
    score: 78,
    confidence: 0.84,
    gate: "通过",
    quality: "结构稳定",
  },
  {
    id: "anon-002",
    studentNumber: "2024214281",
    name: "宋玲芸",
    stage: "已完成",
    docs: "3 份文档",
    score: 83,
    confidence: 0.91,
    gate: "通过",
    quality: "可直接导出",
  },
  {
    id: "anon-003",
    studentNumber: "2024214306",
    name: "吴锐",
    stage: "已完成",
    docs: "3 份文档",
    score: 74,
    confidence: 0.78,
    gate: "通过",
    quality: "低置信度 / 追踪缺失",
  },
  {
    id: "anon-004",
    studentNumber: "2024214312",
    name: "周佳琳",
    stage: "处理中",
    docs: "2 份文档",
    score: "--",
    confidence: "--",
    gate: "待判断",
    quality: "文档缺失",
  },
] as const;

export const analysisStats = [
  { label: "学生总数", value: "48", tone: "neutral" },
  { label: "平均分", value: "74.3", tone: "neutral" },
  { label: "低置信度", value: "4", tone: "risk" },
  { label: "追踪缺失", value: "12", tone: "warn" },
  { label: "门禁异常", value: "3", tone: "risk" },
  { label: "模板残留", value: "2", tone: "warn" },
] as const;

export const analysisNarrative =
  "当前批次成绩主要集中在 70-85 分区间，主要风险来自需求追踪缺失、用例规约展开不足与模板残留。系统整体可继续完成自动阅卷，但导出前建议优先抽查低置信度样本。";

export const filterOptions = [
  { label: "班级", value: "2024级软件工程 3 班" },
  { label: "任务", value: "实验三：需求规格说明书" },
  { label: "得分区间", value: "全部" },
  { label: "问题类型", value: "全部" },
] as const;

export const quickFilters = ["全部", "低置信度", "追踪缺失", "一致性问题", "模板残留"] as const;

export const resultRows = [
  {
    id: "anon-001",
    studentNumber: "2019214047",
    name: "谢雨晨",
    percentileScore: 78,
    grade: "通过",
    confidence: 0.84,
    gateStatus: "通过",
    uncoveredRequirementCount: 1,
    consistencyIssueCount: 1,
    riskTags: ["结构较完整"],
  },
  {
    id: "anon-002",
    studentNumber: "2024214281",
    name: "宋玲芸",
    percentileScore: 83,
    grade: "通过",
    confidence: 0.91,
    gateStatus: "通过",
    uncoveredRequirementCount: 0,
    consistencyIssueCount: 1,
    riskTags: ["可直接导出"],
  },
  {
    id: "anon-003",
    studentNumber: "2024214306",
    name: "吴锐",
    percentileScore: 74,
    grade: "建议关注",
    confidence: 0.78,
    gateStatus: "通过",
    uncoveredRequirementCount: 3,
    consistencyIssueCount: 3,
    riskTags: ["低置信度", "追踪缺失"],
  },
] as const;

export const issueRanks = [
  { title: "薪资结算进度跟踪未覆盖", count: "8 次", tone: "risk" },
  { title: "用例规约缺少异常流", count: "6 次", tone: "warn" },
  { title: "模板占位残留", count: "2 次", tone: "warn" },
] as const;

export const dimensionScores = [
  { name: "需求范围与核心用例清晰度", score: 5, max: 8, confidence: 0.91, status: "warn" },
  { name: "用例图、涉众分析与规约质量", score: 2, max: 9, confidence: 0.96, status: "risk" },
  { name: "需求流程表达与可设计性", score: 4, max: 8, confidence: 0.9, status: "warn" },
  { name: "概要设计对需求的覆盖程度", score: 5, max: 8, confidence: 0.9, status: "warn" },
  { name: "系统架构设计的适配性", score: 2, max: 6, confidence: 0.78, status: "risk" },
  { name: "界面详细设计与需求匹配度", score: 3, max: 6, confidence: 0.88, status: "warn" },
] as const;

export const selectedDimension = {
  name: "概要设计对需求的覆盖程度",
  score: 5,
  max: 8,
  confidence: 0.9,
  evidence:
    "概要设计中覆盖了注册登录、搜索兼职、在线报名、审核录用、双方评价、审核岗位等核心功能，但没有找到“薪资结算进度跟踪”的对应承接。",
  reasoning:
    "多数核心业务在概要设计中能够找到映射，说明存在基础承接链路；但需求中明确列出的结算跟踪功能缺失，使得整体覆盖不完整。",
  matched: [
    "注册登录在概要设计中有对应模块",
    "搜索查看在概要设计中有对应页面和流程",
    "报名、录用、评价、岗位审核均有设计说明",
  ],
  missing: ["薪资结算进度跟踪未覆盖", "实名认证缺少独立承接", "非功能需求承接不足"],
  issues: ["功能需求列表与非功能需求列表没有显式映射，削弱了需求到模块的追踪清晰度。"],
  improvement:
    "建议在概要设计中补充一张“需求-模块-页面-接口”映射表，重点补齐实名认证、结算跟踪和后台管理能力。",
};

export const traceability = {
  extractedRequirements: [
    "岗位发布、搜索报名、审核录用、双方评价的全流程线上化",
    "薪资结算进度跟踪",
    "企业资质与岗位审核",
    "用户信用体系与评价反馈",
  ],
  hldCoverage: [
    { requirement: "岗位发布、搜索报名、审核录用、双方评价的全流程线上化", status: "covered", evidence: "在 4.1-4.7 中均有概要设计展开。" },
    { requirement: "薪资结算进度跟踪", status: "missing", evidence: "没有找到对应模块、页面或接口设计。" },
    { requirement: "企业资质与岗位审核", status: "covered", evidence: "存在独立的审核模块说明。" },
  ],
  lldCoverage: [
    { requirement: "岗位发布、搜索报名、审核录用、双方评价的全流程线上化", status: "weak", evidence: "部分页面和类设计存在，但页面链路仍不完整。" },
    { requirement: "薪资结算进度跟踪", status: "missing", evidence: "详细设计中未找到页面、类或接口。" },
    { requirement: "用户信用体系与评价反馈", status: "weak", evidence: "有流程描述，但缺少完整的数据结构与界面设计。" },
  ],
  uncoveredRequirements: ["薪资结算进度跟踪", "实名认证承接不足"],
};

export const issueSummary = {
  qualityFindings: ["概要设计中仍存在模板章节未替换的问题。", "架构说明与业务承接关系不够明确。", "部分类设计仍残留跨项目术语。"],
  placeholderEnforcement: [
    { criterion: "req_usecase_spec_quality", before: 4, after: 2, reason: "多数用例规约仍为模板占位内容。" },
    { criterion: "hld_architecture_fitness", before: 4, after: 2, reason: "架构章节主体仍是模板说明，缺少有效设计文本。" },
  ],
};

export const gateStatus = [
  { name: "需求文档存在性", passed: true, detail: "requirements present", onFail: "flag" },
  { name: "概要设计文档存在性", passed: true, detail: "hld present", onFail: "flag" },
  { name: "详细设计文档存在性", passed: true, detail: "lld present", onFail: "flag" },
  { name: "重复角色文档检查", passed: true, detail: "no duplicate roles", onFail: "warn" },
] as const;

export const irSummary = {
  documentCount: 3,
  documentRoles: ["requirements", "hld", "lld"],
  wordCount: 17368,
  imageCount: 14,
  logs: ["学生目录识别成功，生成 anon-003。", "成功抽取 3 份文档文本内容。", "识别到需求、概设、详设三类文档角色。"],
};

export const exportStats = [
  { label: "总人数", value: "48", tone: "neutral" },
  { label: "已完成评分", value: "48", tone: "good" },
  { label: "质量提示", value: "7", tone: "warn" },
  { label: "模板版本", value: "v1.0", tone: "neutral" },
] as const;

export const exportSheets = [
  { name: "成绩总表", columns: ["学号", "姓名", "班级", "总分", "等级", "评语"], note: "面向教师与教务导入的主表，默认首个 sheet。" },
  { name: "统计分析", columns: ["平均分", "最高分", "最低分", "分数段分布", "高频问题"], note: "面向课程复盘，不写入教务系统。" },
  { name: "评分明细", columns: ["学生", "维度", "得分", "评分依据", "置信度"], note: "用于抽查解释页对应内容，支持按维度查看。" },
] as const;

export const exportWarnings = [
  "当前批次存在 4 份低置信度样本，建议在正式提交前抽查典型解释页。",
  "2 份样本检测到模板残留，系统已在风险标签中标记。",
  "导出不会被强制拦截，但应在导出记录中保留本次质量提示摘要。",
] as const;

export const exportHistory = [
  { time: "2026-04-17 10:42", name: "软件项目基础实践-实验三-20260417.xlsx", status: "已导出" },
  { time: "2026-04-16 18:05", name: "软件项目基础实践-实验三-预览版.xlsx", status: "字段预览" },
] as const;
