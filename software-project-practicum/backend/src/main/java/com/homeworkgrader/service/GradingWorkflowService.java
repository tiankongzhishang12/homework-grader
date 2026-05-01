package com.homeworkgrader.service;

import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.repository.CrudJdbcRepository;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class GradingWorkflowService {
    private final PythonScriptClient pythonScriptClient;
    private final CrudJdbcRepository repository;
    private final Map<Long, Map<String, Object>> progress = new ConcurrentHashMap<>();

    public GradingWorkflowService(PythonScriptClient pythonScriptClient, CrudJdbcRepository repository) {
        this.pythonScriptClient = pythonScriptClient;
        this.repository = repository;
    }

    public Map<String, Object> start(Long assessmentId) {
        progress.put(assessmentId, mutableProgress("QUEUED", "评分任务已排队", null));
        runAsync(assessmentId);
        return progress.get(assessmentId);
    }

    public Map<String, Object> progress(Long assessmentId) {
        return progress.getOrDefault(assessmentId, mutableProgress("IDLE", "暂无运行中的评分任务", null));
    }

    @Async
    public void runAsync(Long assessmentId) {
        progress.put(assessmentId, mutableProgress("PREPROCESSING", "正在执行内容抽取", null));
        try {
            ScriptResult preprocess = pythonScriptClient.runPreprocess();
            if (!preprocess.success()) {
                progress.put(assessmentId, mutableProgress("FAILED", "内容抽取失败", preprocess));
                return;
            }
            progress.put(assessmentId, mutableProgress("GRADING", "正在执行自动评分", preprocess));
            ScriptResult grading = pythonScriptClient.runGrading();
            if (!grading.success()) {
                progress.put(assessmentId, mutableProgress("FAILED", "自动评分失败", grading));
                return;
            }
            progress.put(assessmentId, mutableProgress("COMPLETED", "评分完成", grading));
        } catch (Exception ex) {
            progress.put(assessmentId, mutableProgress("FAILED", ex.getMessage(), null));
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

    private Map<String, Object> mutableProgress(String status, String message, ScriptResult result) {
        Map<String, Object> map = new HashMap<>();
        map.put("status", status);
        map.put("message", message);
        map.put("scriptResult", result);
        return map;
    }
}
