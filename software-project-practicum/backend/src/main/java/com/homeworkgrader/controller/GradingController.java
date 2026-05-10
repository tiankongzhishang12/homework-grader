package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.domain.GradingMode;
import com.homeworkgrader.dto.GradingStartRequest;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.GradingResultImportService;
import com.homeworkgrader.service.GradingWorkflowService;
import com.homeworkgrader.util.Maps;
import java.util.HashMap;
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

    public GradingController(CrudJdbcRepository repository, GradingResultImportService resultImportService, GradingWorkflowService workflowService) {
        this.repository = repository;
        this.resultImportService = resultImportService;
        this.workflowService = workflowService;
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
}
