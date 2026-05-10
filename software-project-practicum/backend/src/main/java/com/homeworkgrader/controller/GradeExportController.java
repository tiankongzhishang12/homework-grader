package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.service.ExportPrecheckService;
import com.homeworkgrader.service.GradeExportRecordService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class GradeExportController {
    private final ExportPrecheckService exportPrecheckService;
    private final GradeExportRecordService gradeExportRecordService;

    public GradeExportController(ExportPrecheckService exportPrecheckService, GradeExportRecordService gradeExportRecordService) {
        this.exportPrecheckService = exportPrecheckService;
        this.gradeExportRecordService = gradeExportRecordService;
    }

    @GetMapping("/assessments/{assessmentId}/grade-export/precheck")
    public ApiResponse<?> precheck(@PathVariable Long assessmentId) throws Exception {
        return ApiResponse.ok(exportPrecheckService.precheck(assessmentId));
    }

    @GetMapping("/assessments/{assessmentId}/grade-exports")
    public ApiResponse<?> records(@PathVariable Long assessmentId) {
        return ApiResponse.ok(gradeExportRecordService.listByAssessmentId(assessmentId));
    }
}
