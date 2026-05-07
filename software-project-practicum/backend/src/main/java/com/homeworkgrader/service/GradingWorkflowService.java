package com.homeworkgrader.service;

import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.repository.CrudJdbcRepository;
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
    private final Map<Long, Map<String, Object>> progress = new ConcurrentHashMap<>();
    private final ExecutorService gradingExecutor = Executors.newSingleThreadExecutor();

    public GradingWorkflowService(PythonScriptClient pythonScriptClient, CrudJdbcRepository repository) {
        this.pythonScriptClient = pythonScriptClient;
        this.repository = repository;
    }

    public Map<String, Object> start(Long assessmentId) {
        Map<String, Object> queued = newProgress(assessmentId, "QUEUED", "评分任务已排队", null, null);
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
        progress.put(assessmentId, newProgress(assessmentId, "PREPROCESSING", "正在执行内容抽取", null, startedAt));
        try {
            ScriptResult preprocess = pythonScriptClient.runPreprocess();
            if (!preprocess.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "内容抽取失败", preprocess, startedAt));
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "GRADING", "正在执行自动评分", preprocess, startedAt));
            ScriptResult grading = pythonScriptClient.runGrading();
            if (!grading.success()) {
                progress.put(assessmentId, newProgress(assessmentId, "FAILED", "自动评分失败", grading, startedAt));
                return;
            }
            progress.put(assessmentId, newProgress(assessmentId, "COMPLETED", "评分完成", grading, startedAt));
        } catch (Exception ex) {
            progress.put(assessmentId, newProgress(assessmentId, "FAILED", ex.getMessage(), null, startedAt));
        }
    }

    public Long confirm(Long finalResultId, Long teacherId) {
        Map<String, Object> values = new HashMap<>();
        values.put("review_status", "CONFIRMED");
        values.put("confirmed_by_teacher_id", teacherId);
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
        Map<String, Object> map = newProgress(assessmentId, "IDLE", "暂无运行中的评分任务", null, null);
        map.put("startedAt", null);
        return map;
    }

    private Map<String, Object> newProgress(Long assessmentId, String status, String message, ScriptResult result, Object startedAt) {
        Map<String, Object> map = new HashMap<>();
        Object started = startedAt == null ? java.time.Instant.now() : startedAt;
        map.put("assessmentId", assessmentId);
        map.put("status", status);
        map.put("message", message);
        map.put("scriptResult", result);
        map.put("startedAt", started);
        map.put("updatedAt", java.time.Instant.now());
        return map;
    }
}
