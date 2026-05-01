package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.SubmissionService;
import com.homeworkgrader.storage.FileStorageService;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
public class SubmissionController {
    private final CrudJdbcRepository repository;
    private final SubmissionService submissionService;
    private final FileStorageService storageService;

    public SubmissionController(CrudJdbcRepository repository, SubmissionService submissionService, FileStorageService storageService) {
        this.repository = repository;
        this.submissionService = submissionService;
        this.storageService = storageService;
    }

    @PostMapping("/assessments/{id}/submissions/upload")
    public ApiResponse<?> upload(@PathVariable Long id, @RequestParam Long studentId, @RequestParam MultipartFile file) throws IOException {
        return ApiResponse.ok(submissionService.upload(id, studentId, file));
    }

    @GetMapping("/assessments/{id}/submissions")
    public ApiResponse<?> submissions(@PathVariable Long id) {
        return ApiResponse.ok(repository.listBy("submission", "assessment_id", id));
    }

    @GetMapping("/submissions/{id}")
    public ApiResponse<?> submission(@PathVariable Long id) {
        return ApiResponse.ok(repository.get("submission", id));
    }

    @GetMapping("/submissions/{id}/assets/{assetId}/download")
    public ResponseEntity<Resource> download(@PathVariable Long id, @PathVariable Long assetId) throws IOException {
        Map<String, Object> asset = repository.get("submission_asset", assetId);
        if (!id.equals(((Number) asset.get("submission_id")).longValue())) {
            throw new FileNotFoundException("资源不属于该提交");
        }
        Path path = storageService.resolve((String) asset.get("file_path"));
        return ResponseEntity.ok(new FileSystemResource(path));
    }
}
