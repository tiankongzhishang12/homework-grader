package com.homeworkgrader.service;

import com.homeworkgrader.dto.GradeExportData;
import com.homeworkgrader.dto.GradeExportDetailRow;
import com.homeworkgrader.dto.GradeExportMeta;
import com.homeworkgrader.dto.GradeExportRiskRow;
import com.homeworkgrader.dto.GradeExportSummaryRow;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class GradeExportDataService {
    private static final Logger log = LoggerFactory.getLogger(GradeExportDataService.class);

    private final CrudJdbcRepository repository;

    public GradeExportDataService(CrudJdbcRepository repository) {
        this.repository = repository;
    }

    public GradeExportData loadExportData(Long assessmentId, Long exportId) {
        GradeExportData data = new GradeExportData();
        data.setAssessmentId(assessmentId);
        data.setExportId(exportId);
        data.setMeta(loadMeta(assessmentId, exportId));
        data.setSummaryRows(loadSummaryRows(assessmentId));
        data.setDetailRows(loadDetailRows(assessmentId));
        data.setRiskRows(loadRiskRows(assessmentId));
        log.info("Loaded grade export data: assessmentId={}, exportId={}, summaryRows={}, detailRows={}, riskRows={}",
                assessmentId, exportId, data.getSummaryRows().size(), data.getDetailRows().size(), data.getRiskRows().size());
        if (data.getSummaryRows().isEmpty() || data.getDetailRows().isEmpty() || data.getRiskRows().isEmpty()) {
            log.warn("Grade export data contains empty sections: assessmentId={}, exportId={}, summaryRowsEmpty={}, detailRowsEmpty={}, riskRowsEmpty={}",
                    assessmentId, exportId, data.getSummaryRows().isEmpty(), data.getDetailRows().isEmpty(), data.getRiskRows().isEmpty());
        }
        return data;
    }

    private GradeExportMeta loadMeta(Long assessmentId, Long exportId) {
        Map<String, Object> row = repository.query(
                "select ger.id export_id, ger.assessment_id, ger.created_at, ger.export_level, " +
                        "ger.total_students, ger.submitted_students, ger.graded_students, ger.review_required_students, " +
                        "ger.low_confidence_students, ger.warning_count, ger.blocker_count, a.title assessment_title, " +
                        "c.course_name, c.course_code " +
                        "from grade_export_record ger " +
                        "join assessment a on a.id = ger.assessment_id " +
                        "join course_offering co on co.id = a.course_offering_id " +
                        "join course c on c.id = co.course_id " +
                        "where ger.id = :exportId and ger.assessment_id = :assessmentId",
                Maps.of("assessmentId", assessmentId, "exportId", exportId)
        ).get(0);
        GradeExportMeta meta = new GradeExportMeta();
        meta.setExportId(toLong(row.get("export_id")));
        meta.setAssessmentId(toLong(row.get("assessment_id")));
        meta.setAssessmentTitle(toString(row.get("assessment_title")));
        meta.setCourseName(toString(row.get("course_name")));
        meta.setCourseCode(toString(row.get("course_code")));
        meta.setCreatedAt(formatTime(row.get("created_at")));
        meta.setExportLevel(toString(row.get("export_level")));
        meta.setTotalStudents(toInt(row.get("total_students")));
        meta.setSubmittedStudents(toInt(row.get("submitted_students")));
        meta.setGradedStudents(toInt(row.get("graded_students")));
        meta.setReviewRequiredStudents(toInt(row.get("review_required_students")));
        meta.setLowConfidenceStudents(toInt(row.get("low_confidence_students")));
        meta.setWarningCount(toInt(row.get("warning_count")));
        meta.setBlockerCount(toInt(row.get("blocker_count")));
        meta.setFileName("export-" + exportId + ".xlsx");
        return meta;
    }

    private List<GradeExportSummaryRow> loadSummaryRows(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, s.id submission_id, fr.id final_result_id, " +
                        "fr.final_score, fr.score_source, fr.review_status, fr.confirmed_at, " +
                        "gr.confidence, gr.status grading_run_status, gr.model_name " +
                        "from final_result fr " +
                        "join submission s on s.id = fr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "order by st.student_no, s.id",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportSummaryRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            GradeExportSummaryRow item = new GradeExportSummaryRow();
            item.setStudentNo(toString(row.get("student_no")));
            item.setStudentName(toString(row.get("student_name")));
            item.setSubmissionId(toLong(row.get("submission_id")));
            item.setFinalResultId(toLong(row.get("final_result_id")));
            item.setFinalScore(toBigDecimal(row.get("final_score")));
            item.setScoreSource(toString(row.get("score_source")));
            item.setReviewStatus(toString(row.get("review_status")));
            item.setConfirmedAt(formatTime(row.get("confirmed_at")));
            item.setConfidence(toBigDecimal(row.get("confidence")));
            item.setGradingRunStatus(toString(row.get("grading_run_status")));
            item.setModelName(toString(row.get("model_name")));
            result.add(item);
        }
        return result;
    }

    private List<GradeExportDetailRow> loadDetailRows(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, qd.question_no, qd.section_name, rd.rubric_name, " +
                        "sir.item_type, sir.score, sir.max_score, sir.confidence, sir.needs_review, " +
                        "sir.evidence_text, sir.comment_text " +
                        "from score_item_result sir " +
                        "join grading_run gr on gr.id = sir.grading_run_id " +
                        "join submission s on s.id = gr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "left join question_definition qd on qd.id = sir.question_definition_id " +
                        "left join rubric_definition rd on rd.id = sir.rubric_definition_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "order by st.student_no, gr.id, sir.id",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportDetailRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            GradeExportDetailRow item = new GradeExportDetailRow();
            item.setStudentNo(toString(row.get("student_no")));
            item.setStudentName(toString(row.get("student_name")));
            item.setQuestionNo(toString(row.get("question_no")));
            item.setSectionName(toString(row.get("section_name")));
            item.setRubricName(toString(row.get("rubric_name")));
            item.setItemType(toString(row.get("item_type")));
            item.setScore(toBigDecimal(row.get("score")));
            item.setMaxScore(toBigDecimal(row.get("max_score")));
            item.setConfidence(toBigDecimal(row.get("confidence")));
            item.setNeedsReview(toBoolean(row.get("needs_review")));
            item.setEvidenceText(toString(row.get("evidence_text")));
            item.setCommentText(toString(row.get("comment_text")));
            result.add(item);
        }
        return result;
    }

    private List<GradeExportRiskRow> loadRiskRows(Long assessmentId) {
        List<GradeExportRiskRow> result = new ArrayList<>();
        result.addAll(loadReviewStatusRisks(assessmentId));
        result.addAll(loadLowConfidenceRisks(assessmentId));
        result.addAll(loadNeedsReviewRisks(assessmentId));
        result.addAll(loadMissingEvidenceRisks(assessmentId));
        return result;
    }

    private List<GradeExportRiskRow> loadReviewStatusRisks(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, fr.review_status " +
                        "from final_result fr join submission s on s.id = fr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and fr.review_status in ('AI_GENERATED', 'REVIEW_REQUIRED') " +
                        "order by st.student_no",
                Maps.of("assessmentId", assessmentId)
        );
        return toRiskRows(rows, "待教师确认", "最终成绩尚未完成教师确认。", "建议教师复核并确认最终成绩。");
    }

    private List<GradeExportRiskRow> loadLowConfidenceRisks(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, fr.review_status, gr.confidence " +
                        "from final_result fr join submission s on s.id = fr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and gr.confidence is not null and gr.confidence > 0 and gr.confidence < 0.8 " +
                        "order by st.student_no",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportRiskRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toRiskRow(row, "低置信度", "整体置信度低于 0.8，当前值：" + toString(row.get("confidence")), "建议优先抽查该学生评分。"));
        }
        return result;
    }

    private List<GradeExportRiskRow> loadNeedsReviewRisks(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, fr.review_status, qd.question_no, rd.rubric_name " +
                        "from score_item_result sir join grading_run gr on gr.id = sir.grading_run_id " +
                        "join submission s on s.id = gr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "left join final_result fr on fr.selected_grading_run_id = gr.id " +
                        "left join question_definition qd on qd.id = sir.question_definition_id " +
                        "left join rubric_definition rd on rd.id = sir.rubric_definition_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 and sir.needs_review = 1 " +
                        "order by st.student_no, sir.id",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportRiskRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toRiskRow(row, "评分项需复核",
                    "评分项标记为需复核：" + blankToDash(toString(row.get("question_no"))) + " / " + blankToDash(toString(row.get("rubric_name"))),
                    "建议查看评分项证据并确认得分。"));
        }
        return result;
    }

    private List<GradeExportRiskRow> loadMissingEvidenceRisks(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select st.student_no, st.student_name, fr.review_status, qd.question_no, rd.rubric_name " +
                        "from score_item_result sir join grading_run gr on gr.id = sir.grading_run_id " +
                        "join submission s on s.id = gr.submission_id " +
                        "join student st on st.id = s.student_id " +
                        "left join final_result fr on fr.selected_grading_run_id = gr.id " +
                        "left join question_definition qd on qd.id = sir.question_definition_id " +
                        "left join rubric_definition rd on rd.id = sir.rubric_definition_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and (sir.evidence_text is null or trim(sir.evidence_text) = '') " +
                        "and (sir.comment_text is null or trim(sir.comment_text) = '') " +
                        "order by st.student_no, sir.id",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportRiskRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toRiskRow(row, "证据或评语缺失",
                    "评分项缺少证据和评语：" + blankToDash(toString(row.get("question_no"))) + " / " + blankToDash(toString(row.get("rubric_name"))),
                    "建议补充或复核评分依据。"));
        }
        return result;
    }

    private List<GradeExportRiskRow> toRiskRows(List<Map<String, Object>> rows, String type, String reason, String suggestedAction) {
        List<GradeExportRiskRow> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toRiskRow(row, type, reason, suggestedAction));
        }
        return result;
    }

    private GradeExportRiskRow toRiskRow(Map<String, Object> row, String type, String reason, String suggestedAction) {
        GradeExportRiskRow item = new GradeExportRiskRow();
        item.setStudentNo(toString(row.get("student_no")));
        item.setStudentName(toString(row.get("student_name")));
        item.setRiskType(type);
        item.setRiskReason(reason);
        item.setReviewStatus(toString(row.get("review_status")));
        item.setSuggestedAction(suggestedAction);
        return item;
    }

    private String formatTime(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Timestamp) {
            return ((Timestamp) value).toLocalDateTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        }
        return String.valueOf(value);
    }

    private String toString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private Long toLong(Object value) {
        return value instanceof Number ? ((Number) value).longValue() : null;
    }

    private Integer toInt(Object value) {
        return value instanceof Number ? ((Number) value).intValue() : 0;
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value instanceof BigDecimal) {
            return (BigDecimal) value;
        }
        return value instanceof Number ? BigDecimal.valueOf(((Number) value).doubleValue()) : null;
    }

    private Boolean toBoolean(Object value) {
        return value == null ? null : (value instanceof Number ? ((Number) value).intValue() != 0 : Boolean.valueOf(String.valueOf(value)));
    }

    private String blankToDash(String value) {
        return value == null || value.trim().isEmpty() ? "-" : value;
    }
}
