package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.dto.GradeExportPrecheckResponse;
import com.homeworkgrader.service.ExportPrecheckService;
import com.homeworkgrader.service.GradeExportRecordService;
import com.homeworkgrader.storage.FileStorageService;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ExportController {
    private final PythonScriptClient pythonScriptClient;
    private final FileStorageService storageService;
    private final ExportPrecheckService exportPrecheckService;
    private final GradeExportRecordService gradeExportRecordService;

    public ExportController(
            PythonScriptClient pythonScriptClient,
            FileStorageService storageService,
            ExportPrecheckService exportPrecheckService,
            GradeExportRecordService gradeExportRecordService
    ) {
        this.pythonScriptClient = pythonScriptClient;
        this.storageService = storageService;
        this.exportPrecheckService = exportPrecheckService;
        this.gradeExportRecordService = gradeExportRecordService;
    }

    @PostMapping("/assessments/{id}/grades/export")
    public ApiResponse<?> export(@PathVariable Long id) throws Exception {
        GradeExportPrecheckResponse precheck = exportPrecheckService.precheck(id);
        if ("BLOCK".equals(precheck.getExportLevel())) {
            throw new IllegalStateException("当前任务暂不可导出，请先处理阻断问题。");
        }

        Long exportId = gradeExportRecordService.createProcessingRecord(id, precheck);
        ScriptResult result = null;
        try {
            result = pythonScriptClient.runExport();
            Path latest = findLatestReport();
            if (result.success() && latest != null) {
                String fileName = latest.getFileName().toString();
                String relativePath = storageService.workspaceRoot().relativize(latest).toString().replace('\\', '/');
                gradeExportRecordService.markCompleted(exportId, fileName, relativePath, Files.size(latest));
                return ApiResponse.ok(exportResult(id, exportId, "COMPLETED", result, fileName, "成绩导出完成。", null));
            }

            String reason = latest == null ? "未找到生成的 Excel 报表。" : "导出脚本执行失败，退出码：" + result.getExitCode();
            gradeExportRecordService.markFailed(exportId, reason);
            return ApiResponse.ok(exportResult(id, exportId, "FAILED", result, null, "成绩导出失败。", reason));
        } catch (Exception ex) {
            gradeExportRecordService.markFailed(exportId, ex.getMessage());
            return ApiResponse.ok(exportResult(id, exportId, "FAILED", result, null, "成绩导出失败。", ex.getMessage()));
        }
    }

    @PostMapping("/reports/latest/download")
    public ResponseEntity<Resource> latestReport() throws Exception {
        Path latest = findLatestReport();
        if (latest == null) {
            throw new java.io.FileNotFoundException("暂无可下载报表");
        }
        return ResponseEntity.ok(new FileSystemResource(latest));
    }

    private Path findLatestReport() throws Exception {
        return Files.list(storageService.reportsRoot())
                .filter(path -> path.getFileName().toString().endsWith(".xlsx"))
                .max(Comparator.comparing(path -> path.toFile().lastModified()))
                .orElse(null);
    }

    private Map<String, Object> exportResult(Long assessmentId, Long exportId, String status, ScriptResult scriptResult, String report, String message, String failedReason) {
        Map<String, Object> result = new HashMap<>();
        result.put("assessmentId", assessmentId);
        result.put("exportId", exportId);
        result.put("status", status);
        result.put("scriptResult", scriptResult);
        result.put("report", report);
        result.put("message", message);
        result.put("failedReason", failedReason);
        return result;
    }
}
