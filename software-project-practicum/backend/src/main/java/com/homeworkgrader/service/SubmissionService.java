package com.homeworkgrader.service;

import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.storage.FileStorageService;
import com.homeworkgrader.storage.FileStorageService.StoredFile;
import com.homeworkgrader.util.Maps;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class SubmissionService {
    private final CrudJdbcRepository repository;
    private final FileStorageService storageService;

    public SubmissionService(CrudJdbcRepository repository, FileStorageService storageService) {
        this.repository = repository;
        this.storageService = storageService;
    }

    public Map<String, Object> upload(Long assessmentId, Long studentId, MultipartFile file) throws IOException {
        Map<String, Object> attemptParams = new HashMap<>();
        attemptParams.put("assessmentId", assessmentId);
        attemptParams.put("studentId", studentId);
        Integer maxAttempt = repository.queryForInteger(
                "select coalesce(max(attempt_no), 0) from submission where assessment_id = :assessmentId and student_id = :studentId",
                attemptParams
        );
        Map<String, Object> submission = new HashMap<>();
        submission.put("assessment_id", assessmentId);
        submission.put("student_id", studentId);
        submission.put("attempt_no", maxAttempt + 1);
        submission.put("submit_status", "UPLOADED");
        submission.put("submitted_at", LocalDateTime.now());
        submission.put("is_late", 0);
        submission.put("status", 1);
        Long submissionId = repository.insert("submission", submission);
        StoredFile stored = storageService.saveSubmissionFile(assessmentId, studentId, file);
        String ext = extensionOf(stored.getFileName());
        Map<String, Object> asset = new HashMap<>();
        asset.put("submission_id", submissionId);
        asset.put("asset_type", "ORIGINAL");
        asset.put("mime_type", file.getContentType() == null ? "application/octet-stream" : file.getContentType());
        asset.put("file_name", stored.getFileName());
        asset.put("file_ext", ext);
        asset.put("file_path", stored.getRelativePath());
        asset.put("file_hash", stored.getSha256());
        asset.put("file_size", stored.getSize());
        asset.put("version_no", 1);
        Long assetId = repository.insert("submission_asset", asset);
        return Maps.of("submissionId", submissionId, "assetId", assetId, "file", stored);
    }

    private String extensionOf(String name) {
        int dot = name.lastIndexOf('.');
        return dot >= 0 ? name.substring(dot + 1) : "";
    }
}
