package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.dto.GradeExportRecordResponse;
import com.homeworkgrader.service.ExportPrecheckService;
import com.homeworkgrader.service.GradeExportRecordService;
import com.homeworkgrader.storage.FileStorageService;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class GradeExportController {
    private static final Logger log = LoggerFactory.getLogger(GradeExportController.class);

    private final ExportPrecheckService exportPrecheckService;
    private final GradeExportRecordService gradeExportRecordService;
    private final FileStorageService fileStorageService;

    public GradeExportController(
            ExportPrecheckService exportPrecheckService,
            GradeExportRecordService gradeExportRecordService,
            FileStorageService fileStorageService
    ) {
        this.exportPrecheckService = exportPrecheckService;
        this.gradeExportRecordService = gradeExportRecordService;
        this.fileStorageService = fileStorageService;
    }

    @GetMapping("/assessments/{assessmentId}/grade-export/precheck")
    public ApiResponse<?> precheck(@PathVariable Long assessmentId) throws Exception {
        return ApiResponse.ok(exportPrecheckService.precheck(assessmentId));
    }

    @GetMapping("/assessments/{assessmentId}/grade-exports")
    public ApiResponse<?> records(@PathVariable Long assessmentId) {
        return ApiResponse.ok(gradeExportRecordService.listByAssessmentId(assessmentId));
    }

    @GetMapping("/grade-exports/{exportId}/download")
    public ResponseEntity<Resource> download(@PathVariable Long exportId) throws Exception {
        GradeExportRecordResponse record = gradeExportRecordService.getDownloadRecord(exportId);
        String fileName = isBlank(record.getFileName()) ? "grade-export-" + exportId + ".xlsx" : record.getFileName();
        log.info("Starting grade export file download: exportId={}, fileName={}, filePath={}",
                exportId, fileName, record.getFilePath());
        Path file;
        try {
            file = fileStorageService.resolveExportFile(record.getFilePath());
        } catch (Exception ex) {
            log.warn("Grade export file is unavailable: exportId={}, filePath={}", exportId, record.getFilePath());
            log.error("Failed to resolve or read grade export file: exportId={}, filePath={}", exportId, record.getFilePath(), ex);
            throw ex;
        }
        long fileSize = Files.size(file);
        log.info("Grade export file validated for download: exportId={}, fileSize={}", exportId, fileSize);
        ContentDisposition disposition = ContentDisposition.attachment()
                .filename(fileName, StandardCharsets.UTF_8)
                .build();
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .contentLength(fileSize)
                .body(new FileSystemResource(file));
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
