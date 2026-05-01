package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.GradingWorkflowService;
import com.homeworkgrader.util.Maps;
import java.util.Map;
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
    private final CrudJdbcRepository repository;
    private final GradingWorkflowService workflowService;

    public GradingController(CrudJdbcRepository repository, GradingWorkflowService workflowService) {
        this.repository = repository;
        this.workflowService = workflowService;
    }

    @PostMapping("/assessments/{id}/grading/start")
    public ApiResponse<?> start(@PathVariable Long id) {
        return ApiResponse.ok(workflowService.start(id));
    }

    @GetMapping("/assessments/{id}/grading/progress")
    public ApiResponse<?> progress(@PathVariable Long id) {
        return ApiResponse.ok(workflowService.progress(id));
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
        return ApiResponse.ok(repository.query(
                "select fr.*, s.assessment_id, s.student_id, s.attempt_no " +
                        "from final_result fr join submission s on s.id = fr.submission_id " +
                        "where s.assessment_id = :assessmentId order by fr.id desc",
                Maps.of("assessmentId", id)
        ));
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
}
