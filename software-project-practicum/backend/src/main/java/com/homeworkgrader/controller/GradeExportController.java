package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.service.ExportPrecheckService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class GradeExportController {
    private final ExportPrecheckService exportPrecheckService;

    public GradeExportController(ExportPrecheckService exportPrecheckService) {
        this.exportPrecheckService = exportPrecheckService;
    }

    @GetMapping("/assessments/{assessmentId}/grade-export/precheck")
    public ApiResponse<?> precheck(@PathVariable Long assessmentId) throws Exception {
        return ApiResponse.ok(exportPrecheckService.precheck(assessmentId));
    }
}
