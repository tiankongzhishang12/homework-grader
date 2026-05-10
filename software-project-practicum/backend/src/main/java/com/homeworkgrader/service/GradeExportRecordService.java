package com.homeworkgrader.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.dto.GradeExportPrecheckResponse;
import com.homeworkgrader.dto.GradeExportRecordResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.FileNotFoundException;
import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.stereotype.Service;

@Service
public class GradeExportRecordService {
    private static final Logger log = LoggerFactory.getLogger(GradeExportRecordService.class);

    private final CrudJdbcRepository repository;
    private final ObjectMapper objectMapper;

    public GradeExportRecordService(CrudJdbcRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    public Long createProcessingRecord(Long assessmentId, GradeExportPrecheckResponse precheck) {
        GradeExportPrecheckResponse.Summary summary = precheck.getSummary();
        Map<String, Object> values = new HashMap<>();
        values.put("assessment_id", assessmentId);
        values.put("status", "PROCESSING");
        values.put("export_level", precheck.getExportLevel());
        values.put("can_export", precheck.isCanExport() ? 1 : 0);
        values.put("total_students", summary.getTotalStudents());
        values.put("submitted_students", summary.getSubmittedStudents());
        values.put("graded_students", summary.getGradedStudents());
        values.put("confirmed_students", summary.getConfirmedStudents());
        values.put("review_required_students", summary.getReviewRequiredStudents());
        values.put("low_confidence_students", summary.getLowConfidenceStudents());
        values.put("failed_students", summary.getFailedStudents());
        values.put("missing_result_students", summary.getMissingResultStudents());
        values.put("warning_count", precheck.getWarnings().size());
        values.put("blocker_count", precheck.getBlockers().size());
        values.put("risk_summary_json", toJson(precheck));
        values.put("started_at", new Timestamp(System.currentTimeMillis()));
        return repository.insert("grade_export_record", values);
    }

    public void markCompleted(Long exportId, String fileName, String filePath, Long fileSize) {
        Map<String, Object> values = new HashMap<>();
        values.put("status", "COMPLETED");
        values.put("file_name", fileName);
        values.put("file_path", filePath);
        values.put("file_size", fileSize);
        values.put("completed_at", new Timestamp(System.currentTimeMillis()));
        values.put("failed_reason", null);
        repository.update("grade_export_record", exportId, values);
        log.info("Grade export record updated: exportId={}, status={}", exportId, "COMPLETED");
    }

    public void markFailed(Long exportId, String failedReason) {
        Map<String, Object> values = new HashMap<>();
        values.put("status", "FAILED");
        values.put("failed_reason", truncate(failedReason, 4000));
        values.put("completed_at", new Timestamp(System.currentTimeMillis()));
        repository.update("grade_export_record", exportId, values);
        log.info("Grade export record updated: exportId={}, status={}", exportId, "FAILED");
    }

    public List<GradeExportRecordResponse> listByAssessmentId(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select * from grade_export_record where assessment_id = :assessmentId order by created_at desc, id desc",
                Maps.of("assessmentId", assessmentId)
        );
        List<GradeExportRecordResponse> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toResponse(row));
        }
        return result;
    }

    public GradeExportRecordResponse getById(Long exportId) {
        return toResponse(repository.get("grade_export_record", exportId));
    }

    public GradeExportRecordResponse getDownloadRecord(Long exportId) throws FileNotFoundException {
        GradeExportRecordResponse record;
        try {
            record = getById(exportId);
        } catch (EmptyResultDataAccessException ex) {
            throw new FileNotFoundException("Export record was not found.");
        }
        if (!"COMPLETED".equals(record.getStatus())) {
            log.warn("Attempted to download non-completed grade export: exportId={}, status={}", exportId, record.getStatus());
            throw new IllegalStateException("Export record is not completed yet.");
        }
        if (record.getFilePath() == null || record.getFilePath().trim().isEmpty()) {
            log.warn("Grade export record is missing file_path: exportId={}", exportId);
            throw new FileNotFoundException("Export file path is missing.");
        }
        return record;
    }

    private GradeExportRecordResponse toResponse(Map<String, Object> row) {
        GradeExportRecordResponse response = new GradeExportRecordResponse();
        response.setId(toLong(row.get("id")));
        response.setAssessmentId(toLong(row.get("assessment_id")));
        response.setFileName(toString(row.get("file_name")));
        response.setFilePath(toString(row.get("file_path")));
        response.setFileSize(toLong(row.get("file_size")));
        response.setStatus(toString(row.get("status")));
        response.setExportLevel(toString(row.get("export_level")));
        response.setCanExport(toBoolean(row.get("can_export")));
        response.setTotalStudents(toInt(row.get("total_students")));
        response.setSubmittedStudents(toInt(row.get("submitted_students")));
        response.setGradedStudents(toInt(row.get("graded_students")));
        response.setConfirmedStudents(toInt(row.get("confirmed_students")));
        response.setReviewRequiredStudents(toInt(row.get("review_required_students")));
        response.setLowConfidenceStudents(toInt(row.get("low_confidence_students")));
        response.setFailedStudents(toInt(row.get("failed_students")));
        response.setMissingResultStudents(toInt(row.get("missing_result_students")));
        response.setWarningCount(toInt(row.get("warning_count")));
        response.setBlockerCount(toInt(row.get("blocker_count")));
        response.setCreatedAt(formatTime(row.get("created_at")));
        response.setStartedAt(formatTime(row.get("started_at")));
        response.setCompletedAt(formatTime(row.get("completed_at")));
        response.setFailedReason(toString(row.get("failed_reason")));
        return response;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            return "{\"error\":\"failed_to_serialize_precheck\"}";
        }
    }

    private Long toLong(Object value) {
        return value instanceof Number ? ((Number) value).longValue() : null;
    }

    private Integer toInt(Object value) {
        return value instanceof Number ? ((Number) value).intValue() : 0;
    }

    private Boolean toBoolean(Object value) {
        return value == null ? null : (value instanceof Number ? ((Number) value).intValue() != 0 : Boolean.valueOf(String.valueOf(value)));
    }

    private String toString(Object value) {
        return value == null ? null : String.valueOf(value);
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

    private String truncate(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
