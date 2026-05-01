package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
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
        request.put("assessment_id", id);
        return ApiResponse.ok(Maps.of("id", repository.insert("assessment_template", request)));
    }

    @PostMapping("/templates/{id}/questions")
    public ApiResponse<?> createQuestion(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        request.put("template_id", id);
        return ApiResponse.ok(Maps.of("id", repository.insert("question_definition", request)));
    }

    @PostMapping("/templates/{id}/rubrics")
    public ApiResponse<?> createRubric(@PathVariable Long id, @RequestBody Map<String, Object> request) {
        request.put("template_id", id);
        return ApiResponse.ok(Maps.of("id", repository.insert("rubric_definition", request)));
    }
}
