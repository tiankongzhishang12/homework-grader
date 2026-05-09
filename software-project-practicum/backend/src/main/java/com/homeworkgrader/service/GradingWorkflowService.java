package com.homeworkgrader.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.storage.FileStorageService;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
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
    private final GradingWorkspaceService workspaceService;
    private final RubricRuntimeExportService rubricRuntimeExportService;
    private final GraderRuntimeConfigService graderRuntimeConfigService;
    private final FileStorageService storageService;
    private final ObjectMapper objectMapper;
    private final Map<Long, Map<String, Object>> progress = new ConcurrentHashMap<>();
    private final Map<Long, List<Map<String, Object>>> logs = new ConcurrentHashMap<>();
    private final ExecutorService gradingExecutor = Executors.newSingleThreadExecutor();

    public GradingWorkflowService(PythonScriptClient pythonScriptClient, CrudJdbcRepository repository, GradingResultImportService resultImportService, GradingWorkspaceService workspaceService, RubricRuntimeExportService rubricRuntimeExportService, GraderRuntimeConfigService graderRuntimeConfigService, FileStorageService storageService, ObjectMapper objectMapper) {
        this.pythonScriptClient = pythonScriptClient;
        this.repository = repository;
        this.resultImportService = resultImportService;
        this.workspaceService = workspaceService;
        this.rubricRuntimeExportService = rubricRuntimeExportService;
        this.graderRuntimeConfigService = graderRuntimeConfigService;
        this.storageService = storageService;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> start(Long assessmentId) {
        List<Map<String, Object>> currentLogs = new ArrayList<>();
        logs.put(assessmentId, currentLogs);
        appendLog(assessmentId, "info", "Preflight started for assessment " + assessmentId + ".");
        appendPreflightLogs(assessmentId);
        try {
            GradingWorkspaceService.PrepareSummary summary = workspaceService.prepareAssessmentWorkspace(assessmentId);
            appendLog(assessmentId, summary.getCopiedCount() > 0 ? "info" : "error", "Workspace prepared from current assessment submissions: assets=" + summary.getAssetCount() + ", copied=" + summary.getCopiedCount() + ", skipped=" + summary.getSkippedCount() + ".");
            if (summary.getCopiedCount() == 0) {
                Map<String, Object> failed = newProgress(assessmentId, "FAILED", "No supported submission files were copied into the grading workspace.", null, null, null);
                progress.put(assessmentId, failed);
                return failed;
            }
        } catch (Exception ex) {
            appendLog(assessmentId, "error", "Workspace preparation failed: " + ex.getMessage());
            Map<String, Object> failed = newProgress(assessmentId, "FAILED", "Workspace preparation failed: " + ex.getMessage(), null, null, null);
            progress.put(assessmentId, failed);
            return failed;
        }
        Map<String, Object> queued = newProgress(assessmentId, "QUEUED", "Grading task queued.", null, null, null);
        progress.put(assessmentId, queued);
        appendLog(assessmentId, "info", "Grading task queued. The backend worker will run preprocessing first.");
        gradingExecutor.submit(new Runnable() {
            @Override
            public void run() {
                runWorkflow(assessmentId);
            }
        });
        return progress.get(assessmentId);
    }

    public List<Map<String, Object>> logs(Long assessmentId) {
        List<Map<String, Object>> current = new ArrayList<>(logs.getOrDefault(assessmentId, new ArrayList<Map<String, Object>>()));
        appendScriptProgressLogs(current);
        return current;
    }

    public Map<String, Object> progress(Long assessmentId) {
        Map<String, Object> current = progress.getOrDefault(assessmentId, idleProgress(assessmentId));
        if ("GRADING".equals(current.get("status"))) {
            return withScriptProgress(current);
        }
        return current;
    }

    private void runWorkflow(Long assessmentId) {
        Map<String, Object> current = progress.get(assessmentId);
        Object startedAt = current == null ? null : current.get("startedAt");
        progress.put(assessmentId, newProgress(assessmentId, "PREPROCESSING", "Running submission preprocessing.", null, startedAt, null));
        try {
            RubricRuntimeExportService.RuntimeRubric runtimeRubric = rubricRuntimeExportService.exportForAssessment(assessmentId);
            appendLog(assessmentId, "info", "Runtime rubric exported: " + runtimeRubric.getRubricRuntimeId() + ".");
            Path runtimeConfigPath = graderRuntimeConfigService.createRuntimeConfig(assessmentId, runtimeRubric.getRubricYamlPath());
            appendLog(assessmentId, "info", "Runtime grader config created: " + runtimeConfigPath + ".");

            appendLog(assessmentId, "info", "Preprocessing script started.");
            ScriptResult preprocess = pythonScriptClient.runPreprocess(runtimeConfigPath);
            appendScriptResultLogs(assessmentId, "Preprocessing", preprocess);
            if (!preprocess.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Submission preprocessing failed.", preprocess, startedAt, null));
                appendLog(assessmentId, "error", "Preprocessing failed. Grading was not started.");
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "GRADING", "Running automatic grading.", preprocess, startedAt, null));
            appendLog(assessmentId, "info", "Automatic grading script started. Model calls may take several minutes.");
            ScriptResult grading = pythonScriptClient.runGrading(runtimeConfigPath);
            appendScriptResultLogs(assessmentId, "Automatic grading", grading);
            if (!grading.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Automatic grading failed.", grading, startedAt, null));
                appendLog(assessmentId, "error", "Automatic grading failed before score import.");
                return;
            }
            appendLog(assessmentId, "info", "Automatic grading script finished. Importing score JSON files.");
            GradingResultImportService.ImportSummary importSummary = resultImportService.importScores(assessmentId);
            appendLog(assessmentId, "info", "Score import summary: imported=" + importSummary.getImportedCount() + ", skipped=" + importSummary.getSkippedCount() + ", failed=" + importSummary.getFailedCount() + ".");
            if (importSummary.getFailedCount() > 0) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Grading result import failed.", grading, startedAt, importSummary));
                appendLog(assessmentId, "error", "Score import failed for one or more files.");
                return;
            }
            if (importSummary.getImportedCount() == 0) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "Grading script succeeded, but no grading results were imported.", grading, startedAt, importSummary));
                appendLog(assessmentId, "error", "No score JSON files were imported.");
                return;
            }
            if (importSummary.getSkippedCount() > 0) {
                progress.put(assessmentId, newProgress(assessmentId, "COMPLETED", "Some grading results were imported; some were skipped.", grading, startedAt, importSummary));
                appendLog(assessmentId, "warn", "Grading completed with skipped score files. Review import summary before publishing.");
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "COMPLETED", "Grading completed and all results imported.", grading, startedAt, importSummary));
            appendLog(assessmentId, "info", "Grading completed and all imported results are available for analysis.");
        } catch (Exception ex) {
            progress.put(assessmentId, newProgress(assessmentId, "FAILED", ex.getMessage(), null, startedAt, null));
            appendLog(assessmentId, "error", "Workflow exception: " + ex.getMessage());
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

    private Map<String, Object> withScriptProgress(Map<String, Object> current) {
        Map<String, Object> enriched = new HashMap<>(current);
        try {
            Path progressPath = storageService.workspaceRoot().resolve("progress.json").normalize();
            if (!progressPath.startsWith(storageService.workspaceRoot()) || !Files.exists(progressPath)) {
                return enriched;
            }
            Map<String, Object> scriptProgress = objectMapper.readValue(
                    progressPath.toFile(),
                    new TypeReference<Map<String, Object>>() {}
            );
            enriched.put("scriptProgress", scriptProgress);
            Object lastUpdated = scriptProgress.get("last_updated");
            if (lastUpdated != null) {
                enriched.put("updatedAt", lastUpdated);
                Long staleSeconds = staleSeconds(String.valueOf(lastUpdated));
                if (staleSeconds != null) {
                    enriched.put("scriptProgressStaleSeconds", staleSeconds);
                    if (staleSeconds > 180) {
                        enriched.put("message", "Automatic grading is still running, but script progress has not updated for " + staleSeconds + " seconds. The model request may be stalled.");
                    } else {
                        enriched.put("message", "Automatic grading is running. Script progress is updating.");
                    }
                }
            }
        } catch (Exception ex) {
            enriched.put("scriptProgressError", ex.getMessage());
        }
        return enriched;
    }

    private Long staleSeconds(String lastUpdated) {
        try {
            Instant updated = Instant.parse(lastUpdated);
            return Duration.between(updated, Instant.now()).getSeconds();
        } catch (Exception ex) {
            return null;
        }
    }

    private void appendPreflightLogs(Long assessmentId) {
        try {
            Integer submissions = repository.queryForInteger(
                    "select count(*) from submission where assessment_id = :assessmentId",
                    com.homeworkgrader.util.Maps.of("assessmentId", assessmentId)
            );
            appendLog(assessmentId, submissions > 0 ? "info" : "warn", "Preflight submissions: " + submissions + " rows found.");
        } catch (Exception ex) {
            appendLog(assessmentId, "warn", "Preflight could not count submissions: " + ex.getMessage());
        }
        try {
            Integer templates = repository.queryForInteger(
                    "select count(*) from assessment_template where assessment_id = :assessmentId",
                    com.homeworkgrader.util.Maps.of("assessmentId", assessmentId)
            );
            appendLog(assessmentId, templates > 0 ? "info" : "warn", "Preflight templates: " + templates + " rows found.");
        } catch (Exception ex) {
            appendLog(assessmentId, "warn", "Preflight could not count templates: " + ex.getMessage());
        }
    }

    private void appendScriptResultLogs(Long assessmentId, String label, ScriptResult result) {
        appendLog(assessmentId, result.success() ? "info" : "error", label + " script exited with code " + result.getExitCode() + ".");
        appendOutputLog(assessmentId, result.getStdout(), label + " stdout", "info");
        appendOutputLog(assessmentId, result.getStderr(), label + " stderr", result.success() ? "warn" : "error");
    }

    private void appendOutputLog(Long assessmentId, String output, String label, String level) {
        if (output == null || output.trim().isEmpty()) {
            return;
        }
        String compact = output.trim().replaceAll("\\s+", " ");
        if (compact.length() > 600) {
            compact = compact.substring(0, 600) + "...";
        }
        appendLog(assessmentId, level, label + ": " + compact);
    }

    private void appendLog(Long assessmentId, String level, String message) {
        List<Map<String, Object>> current = logs.computeIfAbsent(assessmentId, key -> new ArrayList<Map<String, Object>>());
        Map<String, Object> item = new HashMap<>();
        item.put("time", Instant.now().toString());
        item.put("level", level);
        item.put("message", message);
        current.add(item);
    }

    private void appendScriptProgressLogs(List<Map<String, Object>> target) {
        try {
            Path progressPath = storageService.workspaceRoot().resolve("progress.json").normalize();
            if (!progressPath.startsWith(storageService.workspaceRoot()) || !Files.exists(progressPath)) {
                addTransientLog(target, "info", "Script progress file has not been created yet.");
                return;
            }
            Map<String, Object> scriptProgress = objectMapper.readValue(
                    progressPath.toFile(),
                    new TypeReference<Map<String, Object>>() {}
            );
            addTransientLog(target, "info", "Script progress: completed=" + scriptProgress.get("completed") + ", failed=" + scriptProgress.get("failed") + ", pending=" + scriptProgress.get("pending") + ", total=" + scriptProgress.get("total") + ".");
            Object failedIds = scriptProgress.get("failed_ids");
            if (failedIds instanceof List && !((List<?>) failedIds).isEmpty()) {
                int index = 0;
                for (Object failed : (List<?>) failedIds) {
                    if (index >= 5) {
                        break;
                    }
                    addTransientLog(target, "error", "Failed student: " + String.valueOf(failed));
                    index++;
                }
            }
            Object lastUpdated = scriptProgress.get("last_updated");
            Long stale = lastUpdated == null ? null : staleSeconds(String.valueOf(lastUpdated));
            if (stale != null && stale > 180) {
                addTransientLog(target, "warn", "Script progress has not updated for " + stale + " seconds. The active model request may be stalled.");
            }
        } catch (Exception ex) {
            addTransientLog(target, "warn", "Could not read script progress log: " + ex.getMessage());
        }
    }

    private void addTransientLog(List<Map<String, Object>> target, String level, String message) {
        Map<String, Object> item = new HashMap<>();
        item.put("time", Instant.now().toString());
        item.put("level", level);
        item.put("message", message);
        target.add(item);
    }
}
