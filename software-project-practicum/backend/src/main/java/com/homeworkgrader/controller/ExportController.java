package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.dto.GradeExportData;
import com.homeworkgrader.dto.GradeExportPrecheckResponse;
import com.homeworkgrader.service.ExportPrecheckService;
import com.homeworkgrader.service.GradeExcelWriter;
import com.homeworkgrader.service.GradeExportDataService;
import com.homeworkgrader.service.GradeExportRecordService;
import com.homeworkgrader.storage.FileStorageService;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Stream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
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
    private static final Logger log = LoggerFactory.getLogger(ExportController.class);

    private final FileStorageService storageService;
    private final ExportPrecheckService exportPrecheckService;
    private final GradeExportRecordService gradeExportRecordService;
    private final GradeExportDataService gradeExportDataService;
    private final GradeExcelWriter gradeExcelWriter;

    public ExportController(
            FileStorageService storageService,
            ExportPrecheckService exportPrecheckService,
            GradeExportRecordService gradeExportRecordService,
            GradeExportDataService gradeExportDataService,
            GradeExcelWriter gradeExcelWriter
    ) {
        this.storageService = storageService;
        this.exportPrecheckService = exportPrecheckService;
        this.gradeExportRecordService = gradeExportRecordService;
        this.gradeExportDataService = gradeExportDataService;
        this.gradeExcelWriter = gradeExcelWriter;
    }

    @PostMapping("/assessments/{id}/grades/export")
    public ApiResponse<?> export(@PathVariable Long id) throws Exception {
        GradeExportPrecheckResponse precheck = exportPrecheckService.precheck(id);
        if ("BLOCK".equals(precheck.getExportLevel())) {
            throw new IllegalStateException("当前任务暂不可导出，请先处理阻断问题。");
        }
        if ("WARN".equals(precheck.getExportLevel())) {
            log.warn("Grade export precheck returned WARN: assessmentId={}, warningCount={}, warningTypes={}",
                    id, precheck.getWarnings().size(), warningTypes(precheck));
        }

        Long exportId = gradeExportRecordService.createProcessingRecord(id, precheck);
        log.info("Starting grade export: assessmentId={}, exportId={}, exportLevel={}, warningCount={}, blockerCount={}",
                id, exportId, precheck.getExportLevel(), precheck.getWarnings().size(), precheck.getBlockers().size());
        try {
            Path targetPath = storageService.assessmentReportPath(id, exportId);
            String fileName = targetPath.getFileName().toString();
            GradeExportData data = gradeExportDataService.loadExportData(id, exportId);
            gradeExcelWriter.writeToFile(data, targetPath);
            long fileSize = Files.size(targetPath);
            String relativePath = storageService.toWorkspaceRelativePath(targetPath);
            log.info("Grade export Excel generated: assessmentId={}, exportId={}, fileName={}, filePath={}, fileSize={}",
                    id, exportId, fileName, relativePath, fileSize);
            markCompleted(exportId, fileName, relativePath, fileSize);
            return ApiResponse.ok(exportResult(id, exportId, "COMPLETED", null, fileName, "成绩导出完成。", null));
        } catch (Exception ex) {
            String failedReason = ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage();
            log.error("Grade export failed: assessmentId={}, exportId={}, reason={}", id, exportId, failedReason, ex);
            markFailed(exportId, failedReason);
            return ApiResponse.ok(exportResult(id, exportId, "FAILED", null, null, "成绩导出失败。", failedReason));
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
        Path reportsRoot = storageService.reportsRoot().toAbsolutePath().normalize();
        try (Stream<Path> stream = Files.walk(reportsRoot)) {
            return stream
                    .filter(path -> path.toAbsolutePath().normalize().startsWith(reportsRoot))
                    .filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().endsWith(".xlsx"))
                    .max(Comparator.comparing(path -> path.toFile().lastModified()))
                    .orElse(null);
        }
    }

    private void markCompleted(Long exportId, String fileName, String relativePath, long fileSize) {
        try {
            gradeExportRecordService.markCompleted(exportId, fileName, relativePath, fileSize);
        } catch (Exception ex) {
            log.error("Failed to update grade_export_record: exportId={}, targetStatus={}", exportId, "COMPLETED", ex);
            throw ex;
        }
    }

    private void markFailed(Long exportId, String failedReason) {
        try {
            gradeExportRecordService.markFailed(exportId, failedReason);
        } catch (Exception ex) {
            log.error("Failed to update grade_export_record: exportId={}, targetStatus={}", exportId, "FAILED", ex);
        }
    }

    private String warningTypes(GradeExportPrecheckResponse precheck) {
        StringBuilder builder = new StringBuilder();
        for (GradeExportPrecheckResponse.Issue warning : precheck.getWarnings()) {
            if (builder.length() > 0) {
                builder.append(',');
            }
            builder.append(warning.getType());
        }
        return builder.toString();
    }

    private Map<String, Object> exportResult(Long assessmentId, Long exportId, String status, Object scriptResult, String report, String message, String failedReason) {
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
