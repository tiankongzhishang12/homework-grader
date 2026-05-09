package com.homeworkgrader.service;

import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.storage.FileStorageService;
import com.homeworkgrader.storage.FileStorageService.RawWorkspaceFile;
import com.homeworkgrader.util.Maps;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class GradingWorkspaceService {
    private final CrudJdbcRepository repository;
    private final FileStorageService storageService;

    public GradingWorkspaceService(CrudJdbcRepository repository, FileStorageService storageService) {
        this.repository = repository;
        this.storageService = storageService;
    }

    public PrepareSummary prepareAssessmentWorkspace(Long assessmentId) throws IOException {
        List<Map<String, Object>> rows = repository.query(
                "select s.id submission_id, s.student_id, st.student_no, st.student_name, " +
                        "sa.file_name, sa.file_ext, sa.file_path " +
                        "from submission s " +
                        "join student st on st.id = s.student_id " +
                        "join submission_asset sa on sa.submission_id = s.id and sa.asset_type = 'ORIGINAL' " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and s.attempt_no = (select max(s2.attempt_no) from submission s2 where s2.assessment_id = s.assessment_id and s2.student_id = s.student_id and s2.status = 1) " +
                        "order by st.student_no, s.id",
                Maps.of("assessmentId", assessmentId)
        );

        Path stagingRoot = storageService.workspaceRoot().resolve(".grading-staging").resolve("assessment-" + assessmentId + "-" + System.currentTimeMillis()).normalize();
        Files.createDirectories(stagingRoot);
        int staged = 0;
        int preSkipped = 0;
        for (Map<String, Object> row : rows) {
            String ext = asText(row.get("file_ext"));
            String studentNo = asText(row.get("student_no"));
            if (!isSupported(ext) || isBlank(studentNo) || !studentNo.matches("\\d+")) {
                preSkipped++;
                continue;
            }
            Path source = storageService.resolve(asText(row.get("file_path")));
            Path stagedFile = stagingRoot.resolve("submission-" + row.get("submission_id") + "-" + row.get("file_name")).normalize();
            if (!stagedFile.startsWith(stagingRoot)) {
                preSkipped++;
                continue;
            }
            Files.copy(source, stagedFile, StandardCopyOption.REPLACE_EXISTING);
            row.put("_staged_path", stagedFile);
            staged++;
        }

        storageService.resetGradingRunWorkspace();
        int copied = 0;
        int skipped = preSkipped;
        for (Map<String, Object> row : rows) {
            Path stagedPath = (Path) row.get("_staged_path");
            String studentNo = asText(row.get("student_no"));
            if (stagedPath == null) continue;
            RawWorkspaceFile copiedFile = storageService.copyFileToRawWorkspace(
                    stagedPath,
                    studentNo,
                    fallback(asText(row.get("student_name")), "student"),
                    asText(row.get("file_name"))
            );
            if (copiedFile != null) {
                copied++;
            }
        }
        return new PrepareSummary(rows.size(), copied, skipped);
    }

    private boolean isSupported(String ext) {
        if (ext == null) {
            return false;
        }
        String normalized = ext.trim().toLowerCase();
        return "doc".equals(normalized) || "docx".equals(normalized) || "pdf".equals(normalized);
    }

    private String asText(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String fallback(String value, String fallback) {
        return isBlank(value) ? fallback : value;
    }

    public static class PrepareSummary {
        private final int assetCount;
        private final int copiedCount;
        private final int skippedCount;

        public PrepareSummary(int assetCount, int copiedCount, int skippedCount) {
            this.assetCount = assetCount;
            this.copiedCount = copiedCount;
            this.skippedCount = skippedCount;
        }

        public int getAssetCount() {
            return assetCount;
        }

        public int getCopiedCount() {
            return copiedCount;
        }

        public int getSkippedCount() {
            return skippedCount;
        }
    }
}
