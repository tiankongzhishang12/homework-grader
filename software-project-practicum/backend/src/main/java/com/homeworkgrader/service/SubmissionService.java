package com.homeworkgrader.service;

import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.storage.FileStorageService;
import com.homeworkgrader.storage.FileStorageService.RawWorkspaceFile;
import com.homeworkgrader.storage.FileStorageService.StoredFile;
import com.homeworkgrader.util.Maps;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
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
        Map<String, Object> response = new HashMap<>();
        response.put("submissionId", submissionId);
        response.put("studentId", studentId);
        response.put("assetId", assetId);
        response.put("file", stored.getFileName());
        response.put("message", "作业上传成功，已加入待批改队列。");
        response.put("rawWorkspace", rawWorkspace(true, null, "Stored upload file. Grading raw workspace will be rebuilt when grading starts."));
        return response;
    }

    private Map<String, Object> syncToRawWorkspace(Long studentId, StoredFile stored, String ext) {
        if (!isSupportedRawWorkspaceExtension(ext)) {
            return rawWorkspace(false, null, "Unsupported file extension: ." + (ext == null ? "" : ext));
        }
        List<Map<String, Object>> rows = repository.query(
                "select student_no, student_name from student where id = :studentId and status = 1 limit 1",
                Maps.of("studentId", studentId)
        );
        if (rows.isEmpty()) {
            return rawWorkspace(false, null, "Student not found for studentId: " + studentId);
        }
        String studentNo = asText(rows.get(0).get("student_no"));
        String studentName = asText(rows.get(0).get("student_name"));
        if (isBlank(studentNo)) {
            return rawWorkspace(false, null, "Student number is empty for studentId: " + studentId);
        }
        if (!studentNo.matches("\\d+")) {
            return rawWorkspace(false, null, "Student number is not numeric and cannot be parsed by preprocess_student_dirs.py: " + studentNo);
        }
        if (isBlank(studentName)) {
            studentName = "student";
        }
        try {
            RawWorkspaceFile rawFile = storageService.copyToRawWorkspace(stored.getRelativePath(), studentNo, studentName, stored.getFileName());
            return rawWorkspace(true, rawFile.getRelativePath(), rawFile.getMessage());
        } catch (IOException ex) {
            return rawWorkspace(false, null, "Failed to copy to grading raw workspace: " + ex.getMessage());
        }
    }

    private Map<String, Object> rawWorkspace(boolean synced, String path, String message) {
        Map<String, Object> rawWorkspace = new HashMap<>();
        rawWorkspace.put("synced", synced);
        rawWorkspace.put("path", path);
        rawWorkspace.put("message", message);
        return rawWorkspace;
    }

    private boolean isSupportedRawWorkspaceExtension(String ext) {
        if (ext == null) {
            return false;
        }
        String normalized = ext.trim().toLowerCase();
        return "doc".equals(normalized) || "docx".equals(normalized) || "pdf".equals(normalized);
    }

    private String extensionOf(String name) {
        int dot = name.lastIndexOf('.');
        return dot >= 0 ? name.substring(dot + 1).toLowerCase() : "";
    }

    private String asText(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
