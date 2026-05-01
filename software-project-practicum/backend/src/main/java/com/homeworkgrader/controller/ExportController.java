package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.client.python.PythonScriptClient;
import com.homeworkgrader.client.python.PythonScriptClient.ScriptResult;
import com.homeworkgrader.storage.FileStorageService;
import com.homeworkgrader.util.Maps;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
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

    public ExportController(PythonScriptClient pythonScriptClient, FileStorageService storageService) {
        this.pythonScriptClient = pythonScriptClient;
        this.storageService = storageService;
    }

    @PostMapping("/assessments/{id}/grades/export")
    public ApiResponse<?> export(@PathVariable Long id) throws Exception {
        ScriptResult result = pythonScriptClient.runExport();
        Path latest = Files.list(storageService.reportsRoot())
                .filter(path -> path.getFileName().toString().endsWith(".xlsx"))
                .max(Comparator.comparing(path -> path.toFile().lastModified()))
                .orElse(null);
        return ApiResponse.ok(Maps.of("assessmentId", id, "scriptResult", result, "report", latest == null ? null : latest.getFileName().toString()));
    }

    @PostMapping("/reports/latest/download")
    public ResponseEntity<Resource> latestReport() throws Exception {
        Path latest = Files.list(storageService.reportsRoot())
                .filter(path -> path.getFileName().toString().endsWith(".xlsx"))
                .max(Comparator.comparing(path -> path.toFile().lastModified()))
                .orElseThrow(() -> new java.io.FileNotFoundException("暂无可下载报表"));
        return ResponseEntity.ok(new FileSystemResource(latest));
    }
}
