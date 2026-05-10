package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.domain.GradingMode;
import com.homeworkgrader.dto.GradingStartRequest;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.GradingResultImportService;
import com.homeworkgrader.service.GradingWorkflowService;
import com.homeworkgrader.util.Maps;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class GradingController {
    private static final Logger log = LoggerFactory.getLogger(GradingController.class);

    private final CrudJdbcRepository repository;
    private final GradingResultImportService resultImportService;
    private final GradingWorkflowService workflowService;
    private final ObjectMapper objectMapper;

    public GradingController(CrudJdbcRepository repository, GradingResultImportService resultImportService, GradingWorkflowService workflowService, ObjectMapper objectMapper) {
        this.repository = repository;
        this.resultImportService = resultImportService;
        this.workflowService = workflowService;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/assessments/{id}/grading/start")
    public ApiResponse<?> start(@PathVariable Long id, @RequestBody(required = false) GradingStartRequest request) {
        GradingMode mode = request == null ? GradingMode.INCREMENTAL : request.resolveMode();
        return ApiResponse.ok(workflowService.start(id, mode));
    }

    @PostMapping("/assessments/{id}/grading/import-scores")
    public ApiResponse<?> importScores(@PathVariable Long id) {
        GradingResultImportService.ImportSummary summary = resultImportService.importScores(id);
        return ApiResponse.ok(importScoresResponse(id, summary));
    }

    @GetMapping("/assessments/{id}/grading/progress")
    public ApiResponse<?> progress(@PathVariable Long id) {
        return ApiResponse.ok(workflowService.progress(id));
    }

    @GetMapping("/assessments/{id}/grading/logs")
    public ApiResponse<?> logs(@PathVariable Long id) {
        return ApiResponse.ok(workflowService.logs(id));
    }

    @GetMapping("/grading-runs/{id}")
    public ApiResponse<?> gradingRun(@PathVariable Long id) {
        return ApiResponse.ok(repository.get("grading_run", id));
    }

    @GetMapping("/submissions/{id}/score-items")
    public ApiResponse<?> scoreItems(@PathVariable Long id) {
        return ApiResponse.ok(repository.query(
                "select sir.* from score_item_result sir " +
                        "join grading_run gr on gr.id = sir.grading_run_id " +
                        "where gr.submission_id = :submissionId order by sir.id",
                Maps.of("submissionId", id)
        ));
    }

    @GetMapping("/assessments/{id}/final-results")
    public ApiResponse<?> finalResults(@PathVariable Long id) {
        try {
            List<Map<String, Object>> rows = repository.query(
                    "select fr.*, s.assessment_id, s.id as submission_id, s.student_id, s.attempt_no, " +
                            "st.student_no, st.student_name, gr.confidence as overall_confidence, gr.model_name " +
                            "from final_result fr " +
                            "join submission s on s.id = fr.submission_id " +
                            "join student st on st.id = s.student_id " +
                            "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                            "where s.assessment_id = :assessmentId order by fr.id desc",
                    Maps.of("assessmentId", id)
            );
            log.info("Loaded final results for analysis: assessmentId={}, rowCount={}", id, rows.size());
            return ApiResponse.ok(rows);
        } catch (RuntimeException ex) {
            log.error("Failed to load final results for analysis: assessmentId={}", id, ex);
            throw ex;
        }
    }

    @GetMapping("/final-results/{id}/analysis-detail")
    public ApiResponse<?> finalResultAnalysisDetail(@PathVariable Long id) throws java.io.FileNotFoundException {
        log.info("Loading student analysis detail: finalResultId={}", id);
        try {
            List<Map<String, Object>> rows = repository.query(
                    "select fr.id as final_result_id, fr.submission_id, fr.final_score, fr.score_source, " +
                            "fr.review_status, fr.confirmed_at, fr.confirmed_by_teacher_id, " +
                            "fr.selected_grading_run_id, s.assessment_id, s.student_id, s.attempt_no, " +
                            "st.student_no, st.student_name, gr.id as grading_run_id, gr.confidence, " +
                            "gr.model_name, gr.status as grading_run_status " +
                            "from final_result fr " +
                            "join submission s on s.id = fr.submission_id " +
                            "join student st on st.id = s.student_id " +
                            "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                            "where fr.id = :finalResultId",
                    Maps.of("finalResultId", id)
            );
            if (rows.isEmpty()) {
                log.warn("Student analysis detail not found: finalResultId={}", id);
                throw new java.io.FileNotFoundException("未找到该学生的最终成绩记录。");
            }

            Map<String, Object> base = rows.get(0);
            Long gradingRunId = toLong(base.get("grading_run_id"));
            List<Map<String, Object>> scoreItems = Collections.emptyList();
            if (gradingRunId == null) {
                log.warn("Final result has no grading run for analysis detail: finalResultId={}", id);
            } else {
                scoreItems = repository.query(
                        "select sir.id, sir.item_type, sir.question_definition_id, sir.rubric_definition_id, " +
                                "sir.score, sir.max_score, sir.is_correct, sir.needs_review, sir.confidence, " +
                                "sir.evidence_text, sir.evidence_json, sir.comment_text, " +
                                "qd.question_no, qd.section_name, rd.rubric_code, rd.rubric_name " +
                                "from score_item_result sir " +
                                "left join question_definition qd on qd.id = sir.question_definition_id " +
                                "left join rubric_definition rd on rd.id = sir.rubric_definition_id " +
                                "where sir.grading_run_id = :gradingRunId " +
                                "order by qd.sort_order, sir.id",
                        Maps.of("gradingRunId", gradingRunId)
                );
                if (scoreItems.isEmpty()) {
                    log.warn("No score item results for analysis detail: finalResultId={}, gradingRunId={}", id, gradingRunId);
                }
            }

            Map<String, Object> response = buildStudentAnalysisDetail(base, scoreItems);
            log.info("Loaded student analysis detail: finalResultId={}, submissionId={}, scoreItemCount={}",
                    id, base.get("submission_id"), scoreItems.size());
            return ApiResponse.ok(response);
        } catch (java.io.FileNotFoundException ex) {
            throw ex;
        } catch (RuntimeException ex) {
            log.error("Failed to load student analysis detail: finalResultId={}", id, ex);
            throw ex;
        }
    }

    @PutMapping("/final-results/{id}/confirm")
    public ApiResponse<?> confirm(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        Long teacherId = ((Number) request.get("teacher_id")).longValue();
        return ApiResponse.ok(Maps.of("id", workflowService.confirm(id, teacherId)));
    }

    @PutMapping("/final-results/{id}/adjust")
    public ApiResponse<?> adjust(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", workflowService.adjust(id, request)));
    }

    @PostMapping("/assessments/{id}/grades/publish")
    public ApiResponse<?> publish(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        request.put("assessment_id", id);
        request.putIfAbsent("publish_scope", "ASSESSMENT");
        request.putIfAbsent("publish_status", "PUBLISHED");
        return ApiResponse.ok(Maps.of("id", repository.insert("grade_publish_record", request)));
    }

    private Map<String, Object> importScoresResponse(Long assessmentId, GradingResultImportService.ImportSummary summary) {
        String status = "COMPLETED";
        String message = "Grading score JSON files were imported.";
        if (summary.getFailedCount() > 0) {
            status = "FAILED";
            message = "Grading score import failed.";
        } else if (summary.getImportedCount() == 0) {
            status = "FAILED";
            message = "No grading results were imported from workspace score JSON files.";
        } else if (summary.getSkippedCount() > 0) {
            message = "Some grading results were imported; some were skipped.";
        }
        Map<String, Object> response = new HashMap<>();
        response.put("assessmentId", assessmentId);
        response.put("status", status);
        response.put("message", message);
        response.put("importSummary", summary);
        return response;
    }

    private Map<String, Object> buildStudentAnalysisDetail(Map<String, Object> base, List<Map<String, Object>> scoreItems) {
        String reviewStatus = stringValue(base.get("review_status"), "AI_GENERATED");
        String reviewLabel = reviewStatusLabel(reviewStatus);
        BigDecimal score = decimalValue(base.get("final_score"));
        BigDecimal confidence = decimalValue(base.get("confidence"));
        String finalResultId = stringValue(base.get("final_result_id"), "");
        String submissionId = stringValue(base.get("submission_id"), "");

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("id", stringValue(base.get("student_id"), submissionId));
        response.put("assessmentId", stringValue(base.get("assessment_id"), ""));
        response.put("submissionId", submissionId);
        response.put("finalResultId", finalResultId);
        response.put("studentId", stringValue(base.get("student_id"), ""));
        response.put("name", stringValue(base.get("student_name"), "未知学生"));
        response.put("studentNumber", stringValue(base.get("student_no"), "学号缺失"));
        response.put("anonymousId", submissionId.isEmpty() ? finalResultId : submissionId);
        response.put("score", score);
        response.put("percentileScore", score);
        response.put("grade", "-");
        response.put("confidence", confidence);
        response.put("reviewStatus", reviewStatus);
        response.put("confirmedAt", base.get("confirmed_at"));
        response.put("summary", "该学生当前成绩已生成，请结合评分项明细和复核状态进行确认。");
        response.put("qualityFindings", qualityFindings(reviewLabel, score, reviewStatus));
        response.put("dimensions", dimensions(scoreItems));
        response.put("traceability", traceability());
        response.put("gates", gates(reviewLabel, reviewStatus));
        response.put("materials", materials());
        return response;
    }

    private List<String> qualityFindings(String reviewLabel, BigDecimal score, String reviewStatus) {
        List<String> findings = new ArrayList<>();
        findings.add("当前复核状态：" + reviewLabel);
        findings.add("系统评分：" + (score == null ? "-" : score.stripTrailingZeros().toPlainString()) + " 分");
        findings.add(isTeacherActionRequired(reviewStatus) ? "当前成绩尚未完成教师确认。" : "当前成绩已完成确认或发布。");
        return findings;
    }

    private List<Map<String, Object>> dimensions(List<Map<String, Object>> scoreItems) {
        List<Map<String, Object>> dimensions = new ArrayList<>();
        for (int i = 0; i < scoreItems.size(); i++) {
            Map<String, Object> item = scoreItems.get(i);
            Map<String, Object> evidenceJson = parseEvidenceJson(item.get("evidence_json"), item.get("id"));
            Map<String, Object> dimension = new LinkedHashMap<>();
            dimension.put("id", stringValue(item.get("id"), "score-item-" + (i + 1)));
            dimension.put("name", firstText(
                    evidenceJson.get("criterion_name"),
                    item.get("rubric_name"),
                    item.get("rubric_code"),
                    item.get("question_no"),
                    "评分项 " + (i + 1)
            ));
            dimension.put("score", decimalValue(item.get("score")));
            dimension.put("maxScore", decimalValue(item.get("max_score")));
            dimension.put("confidence", decimalValue(item.get("confidence")));
            dimension.put("evidence", firstText(item.get("evidence_text"), "当前评分项暂未返回评分证据。"));
            dimension.put("reasoning", firstText(evidenceJson.get("reasoning"), item.get("comment_text"), "当前评分项暂未返回评语。"));
            dimension.put("matched", stringList(evidenceJson.get("matched_core_points")));
            dimension.put("missing", stringList(evidenceJson.get("missing_points")));
            dimension.put("improvement", firstText(evidenceJson.get("improvement"), "当前评分项暂未返回改进建议。"));
            dimensions.add(dimension);
        }
        return dimensions;
    }

    private Map<String, Object> parseEvidenceJson(Object raw, Object scoreItemId) {
        if (raw == null) {
            return Collections.emptyMap();
        }
        try {
            return objectMapper.readValue(String.valueOf(raw), new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception ex) {
            log.warn("Failed to parse evidence_json for analysis detail: scoreItemId={}", scoreItemId);
            return Collections.emptyMap();
        }
    }

    private Map<String, Object> traceability() {
        Map<String, Object> traceability = new LinkedHashMap<>();
        traceability.put("requirements", Collections.emptyList());
        traceability.put("hldCoverage", Collections.emptyList());
        traceability.put("lldCoverage", Collections.emptyList());
        traceability.put("uncoveredRequirements", Collections.emptyList());
        return traceability;
    }

    private List<Map<String, Object>> gates(String reviewLabel, String reviewStatus) {
        Map<String, Object> gate = new LinkedHashMap<>();
        gate.put("name", "复核状态");
        gate.put("passed", isTerminalReviewStatus(reviewStatus));
        gate.put("detail", "当前状态：" + reviewLabel);
        gate.put("onFail", "建议操作：教师确认或调整后再发布成绩。");
        return Collections.singletonList(gate);
    }

    private Map<String, Object> materials() {
        Map<String, Object> materials = new LinkedHashMap<>();
        materials.put("documentCount", 0);
        materials.put("wordCount", 0);
        materials.put("imageCount", 0);
        materials.put("roles", Collections.emptyList());
        materials.put("logs", Collections.emptyList());
        return materials;
    }

    private boolean isTeacherActionRequired(String status) {
        String normalized = normalizeReviewStatus(status);
        return "AI_GENERATED".equals(normalized) || "REVIEW_REQUIRED".equals(normalized) || "NEEDS_REVIEW".equals(normalized);
    }

    private boolean isTerminalReviewStatus(String status) {
        String normalized = normalizeReviewStatus(status);
        return "CONFIRMED".equals(normalized) || "PUBLISHED".equals(normalized) || "ADJUSTED".equals(normalized);
    }

    private String reviewStatusLabel(String status) {
        String normalized = normalizeReviewStatus(status);
        if ("NEEDS_REVIEW".equals(normalized) || "REVIEW_REQUIRED".equals(normalized)) {
            return "待教师复核";
        }
        if ("AI_GENERATED".equals(normalized)) {
            return "待教师确认";
        }
        if ("CONFIRMED".equals(normalized)) {
            return "已确认";
        }
        if ("ADJUSTED".equals(normalized)) {
            return "已调整";
        }
        if ("PUBLISHED".equals(normalized)) {
            return "已发布";
        }
        return "待确认";
    }

    private String normalizeReviewStatus(String status) {
        return status == null ? "" : status.trim().toUpperCase();
    }

    private String firstText(Object... values) {
        for (Object value : values) {
            if (value != null && !String.valueOf(value).trim().isEmpty()) {
                return String.valueOf(value);
            }
        }
        return "";
    }

    private List<String> stringList(Object value) {
        if (!(value instanceof List)) {
            return Collections.emptyList();
        }
        List<?> raw = (List<?>) value;
        List<String> result = new ArrayList<>();
        for (Object item : raw) {
            if (item != null && !String.valueOf(item).trim().isEmpty()) {
                result.add(String.valueOf(item));
            }
        }
        return result;
    }

    private String stringValue(Object value, String fallback) {
        return value == null ? fallback : String.valueOf(value);
    }

    private BigDecimal decimalValue(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof BigDecimal) {
            return (BigDecimal) value;
        }
        if (value instanceof Number) {
            return BigDecimal.valueOf(((Number) value).doubleValue());
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private Long toLong(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }
}
