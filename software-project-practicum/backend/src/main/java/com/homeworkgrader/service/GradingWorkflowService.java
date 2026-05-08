package com.homeworkgrader.service;

import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.repository.CrudJdbcRepository;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.annotation.PreDestroy;
import org.springframework.stereotype.Service;

@Service
public class GradingWorkflowService {
    private final PythonScriptClient pythonScriptClient;
    private final CrudJdbcRepository repository;
    private final GradingResultImportService resultImportService;
    private final Map<Long, Map<String, Object>> progress = new ConcurrentHashMap<>();
    private final ExecutorService gradingExecutor = Executors.newSingleThreadExecutor();

    public GradingWorkflowService(PythonScriptClient pythonScriptClient, CrudJdbcRepository repository, GradingResultImportService resultImportService) {
        this.pythonScriptClient = pythonScriptClient;
        this.repository = repository;
        this.resultImportService = resultImportService;
    }

    public Map<String, Object> start(Long assessmentId) {
        Map<String, Object> queued = newProgress(assessmentId, "QUEUED", "Grading task queued.", null, null, null);
        progress.put(assessmentId, queued);
        gradingExecutor.submit(new Runnable() {
            @Override
            public void run() {
                runWorkflow(assessmentId);
            }
        });
        return progress.get(assessmentId);
    }

    public Map<String, Object> progress(Long assessmentId) {
        return progress.getOrDefault(assessmentId, idleProgress(assessmentId));
    }

    private void runWorkflow(Long assessmentId) {
        Map<String, Object> current = progress.get(assessmentId);
        Object startedAt = current == null ? null : current.get("startedAt");
        progress.put(assessmentId, newProgress(assessmentId, "PREPROCESSING", "Running submission preprocessing.", null, startedAt, null));
        try {
            ScriptResult preprocess = pythonScriptClient.runPreprocess();
            if (!preprocess.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Submission preprocessing failed.", preprocess, startedAt, null));
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "GRADING", "Running automatic grading.", preprocess, startedAt, null));
            ScriptResult grading = pythonScriptClient.runGrading();
            if (!grading.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Automatic grading failed.", grading, startedAt, null));
                return;
            }
            GradingResultImportService.ImportSummary importSummary = resultImportService.importScores(assessmentId);
            if (importSummary.getFailedCount() > 0) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Grading result import failed.", grading, startedAt, importSummary));
                return;
            }
            if (importSummary.getImportedCount() == 0) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Grading script succeeded, but no grading results were imported.", grading, startedAt, importSummary));
                return;
            }
            if (importSummary.getSkippedCount() > 0) {
                progress.put(assessmentId, newProgress(assessmentId, "COMPLETED", "Some grading results were imported; some were skipped.", grading, startedAt, importSummary));
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "COMPLETED", "Grading completed and all results imported.", grading, startedAt, importSummary));
        } catch (Exception ex) {
            progress.put(assessmentId, newProgress(assessmentId, "FAILED", ex.getMessage(), null, startedAt, null));
        }
    }

    public Long confirm(Long finalResultId, Long teacherId) {
        Map<String, Object> values = new HashMap<>();
        values.put("review_status", "CONFIRMED");
        values.put("confirmed_by_teacher_id", teacherId);
        values.put("confirmed_at", LocalDateTime.now());
        repository.update("final_result", finalResultId, values);
        return finalResultId;
    }

    public Long adjust(Long finalResultId, Map<String, Object> request) {
        Map<String, Object> values = new HashMap<>();
        if (request.containsKey("final_score")) {
            values.put("final_score", request.get("final_score"));
        }
        values.put("score_source", "TEACHER_ADJUSTED");
        values.put("review_status", "ADJUSTED");
        repository.update("final_result", finalResultId, values);
        return finalResultId;
    }

    @PreDestroy
    public void shutdown() {
        gradingExecutor.shutdown();
    }

    private Map<String, Object> idleProgress(Long assessmentId) {
        Map<String, Object> map = newProgress(assessmentId, "IDLE", "No running grading task.", null, null, null);
        map.put("startedAt", null);
        return map;
    }

    private Map<String, Object> newProgress(Long assessmentId, String status, String message, ScriptResult result, Object startedAt, Object importSummary) {
        Map<String, Object> map = new HashMap<>();
        Object started = startedAt == null ? java.time.Instant.now() : startedAt;
        map.put("assessmentId", assessmentId);
        map.put("status", status);
        map.put("message", message);
        map.put("scriptResult", result);
        map.put("importSummary", importSummary);
        map.put("startedAt", started);
        map.put("updatedAt", java.time.Instant.now());
        return map;
    }
}
