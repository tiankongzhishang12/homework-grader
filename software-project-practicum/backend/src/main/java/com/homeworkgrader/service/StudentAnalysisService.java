package com.homeworkgrader.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.dto.StudentAnalysisDetailResponse;
import com.homeworkgrader.dto.StudentAnalysisDimensionResponse;
import com.homeworkgrader.dto.StudentAnalysisGateResponse;
import com.homeworkgrader.dto.StudentAnalysisMaterialsResponse;
import com.homeworkgrader.dto.StudentAnalysisTraceabilityResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.FileNotFoundException;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class StudentAnalysisService {
    private static final Logger log = LoggerFactory.getLogger(StudentAnalysisService.class);

    private final CrudJdbcRepository repository;
    private final ObjectMapper objectMapper;

    public StudentAnalysisService(CrudJdbcRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    public StudentAnalysisDetailResponse getAnalysisDetail(Long finalResultId) throws FileNotFoundException {
        log.info("Loading student analysis detail: finalResultId={}", finalResultId);
        try {
            Map<String, Object> base = loadBaseInfo(finalResultId);
            Long gradingRunId = toLong(base.get("grading_run_id"));
            List<Map<String, Object>> scoreItems = gradingRunId == null ? Collections.emptyList() : loadScoreItems(finalResultId, gradingRunId);
            if (gradingRunId == null) {
                log.warn("Final result has no grading run for analysis detail: finalResultId={}", finalResultId);
            }
            StudentAnalysisDetailResponse response = buildResponse(base, scoreItems);
            log.info("Loaded student analysis detail: finalResultId={}, submissionId={}, scoreItemCount={}",
                    finalResultId, base.get("submission_id"), scoreItems.size());
            return response;
        } catch (FileNotFoundException ex) {
            throw ex;
        } catch (RuntimeException ex) {
            log.error("Failed to load student analysis detail: finalResultId={}", finalResultId, ex);
            throw ex;
        }
    }

    private Map<String, Object> loadBaseInfo(Long finalResultId) throws FileNotFoundException {
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
                Maps.of("finalResultId", finalResultId)
        );
        if (rows.isEmpty()) {
            log.warn("Student analysis detail not found: finalResultId={}", finalResultId);
            throw new FileNotFoundException("未找到该学生的最终成绩记录。");
        }
        return rows.get(0);
    }

    private List<Map<String, Object>> loadScoreItems(Long finalResultId, Long gradingRunId) {
        List<Map<String, Object>> scoreItems = repository.query(
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
            log.warn("No score item results for analysis detail: finalResultId={}, gradingRunId={}", finalResultId, gradingRunId);
        }
        return scoreItems;
    }

    private StudentAnalysisDetailResponse buildResponse(Map<String, Object> base, List<Map<String, Object>> scoreItems) {
        String reviewStatus = stringValue(base.get("review_status"), "AI_GENERATED");
        BigDecimal score = decimalValue(base.get("final_score"));
        BigDecimal confidence = decimalValue(base.get("confidence"));
        String finalResultId = stringValue(base.get("final_result_id"), "");
        String submissionId = stringValue(base.get("submission_id"), "");

        StudentAnalysisDetailResponse response = new StudentAnalysisDetailResponse();
        response.setId(stringValue(base.get("student_id"), submissionId));
        response.setAssessmentId(stringValue(base.get("assessment_id"), ""));
        response.setSubmissionId(submissionId);
        response.setFinalResultId(finalResultId);
        response.setStudentId(stringValue(base.get("student_id"), ""));
        response.setName(stringValue(base.get("student_name"), "未知学生"));
        response.setStudentNumber(stringValue(base.get("student_no"), "学号缺失"));
        response.setAnonymousId(submissionId.isEmpty() ? finalResultId : submissionId);
        response.setScore(score);
        response.setPercentileScore(score);
        response.setGrade("-");
        response.setConfidence(confidence);
        response.setReviewStatus(reviewStatus);
        response.setConfirmedAt(base.get("confirmed_at"));
        response.setSummary("该学生当前成绩已生成，请结合评分项明细和复核状态进行确认。");
        response.setQualityFindings(buildQualityFindings(reviewStatus, score));
        response.setDimensions(buildDimensions(scoreItems));
        response.setTraceability(emptyTraceability());
        response.setGates(buildGates(reviewStatus));
        response.setMaterials(emptyMaterials());
        return response;
    }

    private List<String> buildQualityFindings(String reviewStatus, BigDecimal score) {
        List<String> findings = new ArrayList<>();
        findings.add("当前复核状态：" + reviewStatusLabel(reviewStatus));
        findings.add("系统评分：" + (score == null ? "-" : score.stripTrailingZeros().toPlainString()) + " 分");
        findings.add(isTeacherActionRequired(reviewStatus) ? "当前成绩尚未完成教师确认。" : "当前成绩已完成确认或发布。");
        return findings;
    }

    private List<StudentAnalysisDimensionResponse> buildDimensions(List<Map<String, Object>> scoreItems) {
        List<StudentAnalysisDimensionResponse> dimensions = new ArrayList<>();
        for (int i = 0; i < scoreItems.size(); i++) {
            Map<String, Object> item = scoreItems.get(i);
            Map<String, Object> evidenceJson = parseEvidenceJson(item.get("evidence_json"), item.get("id"));

            StudentAnalysisDimensionResponse dimension = new StudentAnalysisDimensionResponse();
            dimension.setId(stringValue(item.get("id"), "score-item-" + (i + 1)));
            dimension.setName(firstText(
                    evidenceJson.get("criterion_name"),
                    item.get("rubric_name"),
                    item.get("rubric_code"),
                    item.get("question_no"),
                    "评分项 " + (i + 1)
            ));
            dimension.setScore(decimalValue(item.get("score")));
            dimension.setMaxScore(decimalValue(item.get("max_score")));
            dimension.setConfidence(decimalValue(item.get("confidence")));
            dimension.setEvidence(firstText(item.get("evidence_text"), "当前评分项暂未返回评分证据。"));
            dimension.setReasoning(firstText(evidenceJson.get("reasoning"), item.get("comment_text"), "当前评分项暂未返回评语。"));
            dimension.setMatched(stringList(evidenceJson.get("matched_core_points")));
            dimension.setMissing(stringList(evidenceJson.get("missing_points")));
            dimension.setImprovement(firstText(evidenceJson.get("improvement"), "当前评分项暂未返回改进建议。"));
            dimensions.add(dimension);
        }
        return dimensions;
    }

    private List<StudentAnalysisGateResponse> buildGates(String reviewStatus) {
        StudentAnalysisGateResponse gate = new StudentAnalysisGateResponse();
        gate.setName("复核状态");
        gate.setPassed(isTerminalReviewStatus(reviewStatus));
        gate.setDetail("当前状态：" + reviewStatusLabel(reviewStatus));
        gate.setOnFail("建议操作：教师确认或调整后再发布成绩。");
        return Collections.singletonList(gate);
    }

    private StudentAnalysisTraceabilityResponse emptyTraceability() {
        return new StudentAnalysisTraceabilityResponse();
    }

    private StudentAnalysisMaterialsResponse emptyMaterials() {
        return new StudentAnalysisMaterialsResponse();
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
