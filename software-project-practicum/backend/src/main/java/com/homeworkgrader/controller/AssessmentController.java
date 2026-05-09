package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class AssessmentController {
    private final CrudJdbcRepository repository;

    public AssessmentController(CrudJdbcRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/assessments")
    public ApiResponse<?> assessments() {
        return ApiResponse.ok(repository.list("assessment"));
    }

    @PostMapping("/assessments")
    public ApiResponse<?> createAssessment(@RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", repository.insert("assessment", request)));
    }

    @GetMapping("/assessments/{id}")
    public ApiResponse<?> assessment(@PathVariable Long id) {
        return ApiResponse.ok(repository.get("assessment", id));
    }

    @PostMapping("/assessments/{id}/templates")
    public ApiResponse<?> createTemplate(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        Integer versionNo = integerValue(request.get("version_no"), 1);
        Long existingId = findExistingId(
                "select id from assessment_template where assessment_id = :assessmentId and version_no = :versionNo limit 1",
                Maps.of("assessmentId", id, "versionNo", versionNo)
        );
        if (existingId != null) {
            return ApiResponse.ok(Maps.of("id", existingId));
        }

        Map<String, Object> values = new LinkedHashMap<>();
        values.put("assessment_id", id);
        values.put("template_name", stringValue(request.get("template_name"), "Assessment Template"));
        values.put("template_type", stringValue(request.get("template_type"), "REPORT"));
        values.put("version_no", versionNo);
        values.put("total_score", decimalValue(request.get("total_score"), request.get("max_score")));
        values.put("is_active", integerValue(request.get("is_active"), integerValue(request.get("status"), 1)));
        return ApiResponse.ok(Maps.of("id", repository.insert("assessment_template", values)));
    }

    @PostMapping("/templates/{id}/questions")
    public ApiResponse<?> createQuestion(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        String questionNo = stringValue(request.get("question_no"), "Q1");
        Long existingId = findExistingId(
                "select id from question_definition where template_id = :templateId and question_no = :questionNo limit 1",
                Maps.of("templateId", id, "questionNo", questionNo)
        );
        if (existingId != null) {
            return ApiResponse.ok(Maps.of("id", existingId));
        }

        Map<String, Object> values = new LinkedHashMap<>();
        values.put("template_id", id);
        values.put("question_no", questionNo);
        values.put("question_type", stringValue(request.get("question_type"), "REPORT"));
        values.put("section_name", stringValue(request.get("section_name"), null));
        values.put("max_score", decimalValue(request.get("max_score"), request.get("total_score")));
        values.put("scoring_rule", stringValue(request.get("scoring_rule"), stringValue(request.get("question_text"), null)));
        values.put("sort_order", integerValue(request.get("sort_order"), 1));
        return ApiResponse.ok(Maps.of("id", repository.insert("question_definition", values)));
    }

    @PostMapping("/templates/{id}/rubrics")
    public ApiResponse<?> createRubric(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("template_id", id);
        values.put("rubric_code", stringValue(request.get("rubric_code"), "RUBRIC-" + System.currentTimeMillis()));
        values.put("rubric_name", stringValue(request.get("rubric_name"), "Rubric"));
        values.put("max_score", decimalValue(request.get("max_score"), request.get("total_score")));
        values.put("description", stringValue(request.get("description"), null));
        values.put("deduction_rule", stringValue(request.get("deduction_rule"), stringValue(request.get("rubric_json"), null)));
        values.put("sort_order", integerValue(request.get("sort_order"), 1));
        return ApiResponse.ok(Maps.of("id", repository.insert("rubric_definition", values)));
    }

    private String stringValue(Object value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? fallback : text;
    }

    private BigDecimal decimalValue(Object primary, Object secondary) {
        Object value = primary == null ? secondary : primary;
        if (value == null) {
            return BigDecimal.valueOf(100);
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return BigDecimal.valueOf(100);
        }
    }

    private Integer integerValue(Object value, Integer fallback) {
        if (value == null) {
            return fallback;
        }
        try {
            return Integer.valueOf(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return fallback;
        }
    }

    private Long findExistingId(String sql, Map<String, Object> params) {
        java.util.List<Map<String, Object>> rows = repository.query(sql, params);
        if (rows.isEmpty() || rows.get(0).get("id") == null) {
            return null;
        }
        Object id = rows.get(0).get("id");
        if (id instanceof Number) {
            return ((Number) id).longValue();
        }
        return Long.valueOf(String.valueOf(id));
    }
}
