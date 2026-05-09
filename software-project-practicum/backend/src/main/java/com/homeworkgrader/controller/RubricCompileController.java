package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.dto.RubricCompileRequest;
import com.homeworkgrader.dto.RubricCompileResponse;
import com.homeworkgrader.service.RubricCompilerService;
import java.math.BigDecimal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class RubricCompileController {
    private final RubricCompilerService rubricCompilerService;

    public RubricCompileController(RubricCompilerService rubricCompilerService) {
        this.rubricCompilerService = rubricCompilerService;
    }

    @PostMapping("/templates/{templateId}/rubrics/compile")
    public ApiResponse<RubricCompileResponse> compile(
            @PathVariable Long templateId,
            @RequestBody RubricCompileRequest request
    ) {
        if (request == null || request.getTeacherText() == null || request.getTeacherText().trim().isEmpty()) {
            throw new IllegalArgumentException("请先输入中文评分标准。");
        }
        if (request.getTotalScore() == null || request.getTotalScore().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("任务总分必须为正数。");
        }
        return ApiResponse.ok(rubricCompilerService.compile(templateId, request));
    }
}
