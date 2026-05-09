package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.service.StandardAnswerService;
import com.homeworkgrader.util.Maps;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
public class StandardAnswerController {
    private final StandardAnswerService standardAnswerService;

    public StandardAnswerController(StandardAnswerService standardAnswerService) {
        this.standardAnswerService = standardAnswerService;
    }

    @PostMapping("/questions/{questionId}/standard-answers")
    public ApiResponse<?> create(@PathVariable Long questionId, @RequestBody Map<String, Object> request) throws Exception {
        return ApiResponse.ok(Maps.of("id", standardAnswerService.create(questionId, request)));
    }

    @PostMapping("/questions/{questionId}/standard-answers/upload")
    public ApiResponse<?> upload(@PathVariable Long questionId, @RequestParam("file") MultipartFile file) throws Exception {
        return ApiResponse.ok(Maps.of("id", standardAnswerService.createFromFile(questionId, file)));
    }

    @GetMapping("/questions/{questionId}/standard-answers")
    public ApiResponse<?> listByQuestion(@PathVariable Long questionId) {
        return ApiResponse.ok(standardAnswerService.listByQuestion(questionId));
    }

    @GetMapping("/standard-answers/{id}")
    public ApiResponse<?> get(@PathVariable Long id) {
        return ApiResponse.ok(standardAnswerService.get(id));
    }
}
