package com.homeworkgrader.service;

import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.domain.GradingMode;
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
        return prepareAssessmentWorkspace(assessmentId, GradingMode.FULL, null);
    }

    public PrepareSummary prepareAssessmentWorkspace(Long assessmentId, GradingMode mode, Long rubricDefinitionId) throws IOException {
        List<Map<String, Object>> allLatestRows = latestSubmissionRows(assessmentId);
        List<Map<String, Object>> rows = mode == GradingMode.INCREMENTAL
                ? incrementalSubmissionRows(assessmentId, rubricDefinitionId)
                : allLatestRows;
        if (mode == GradingMode.INCREMENTAL && rows.isEmpty()) {
            return new PrepareSummary(mode.name(), allLatestRows.size(), 0, 0, 0, true, "当前没有新增、更新或受影响的提交需要批改。");
        }

        // 第一版增量范围按 latest submission + grading_run.rubric_version 判断。
        // 后续可扩展到 submission_batch_id / submission_type / question scope。
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
        return new PrepareSummary(mode.name(), allLatestRows.size(), rows.size(), copied, skipped, false, "");
    }

    private List<Map<String, Object>> latestSubmissionRows(Long assessmentId) {
        return repository.query(
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
    }

    private List<Map<String, Object>> incrementalSubmissionRows(Long assessmentId, Long rubricDefinitionId) {
        String runtimeRubricId = "db-rubric-" + rubricDefinitionId;
        return repository.query(
                "select s.id submission_id, s.student_id, st.student_no, st.student_name, " +
                        "sa.file_name, sa.file_ext, sa.file_path " +
                        "from submission s " +
                        "join student st on st.id = s.student_id " +
                        "join submission_asset sa on sa.submission_id = s.id and sa.asset_type = 'ORIGINAL' " +
                        "left join final_result fr on fr.submission_id = s.id " +
                        "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and s.attempt_no = (select max(s2.attempt_no) from submission s2 where s2.assessment_id = s.assessment_id and s2.student_id = s.student_id and s2.status = 1) " +
                        "and (fr.id is null or fr.selected_grading_run_id is null or gr.id is null or gr.status <> 'COMPLETED' or gr.rubric_version <> :runtimeRubricId) " +
                        "order by st.student_no, s.id",
                Maps.of("assessmentId", assessmentId, "runtimeRubricId", runtimeRubricId)
        );
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
        private final String mode;
        private final int candidateCount;
        private final int copiedCount;
        private final int skippedCount;
        private final boolean noOp;
        private final String reason;

        public PrepareSummary(int assetCount, int copiedCount, int skippedCount) {
            this("FULL", assetCount, assetCount, copiedCount, skippedCount, false, "");
        }

        public PrepareSummary(String mode, int assetCount, int candidateCount, int copiedCount, int skippedCount, boolean noOp, String reason) {
            this.mode = mode;
            this.assetCount = assetCount;
            this.candidateCount = candidateCount;
            this.copiedCount = copiedCount;
            this.skippedCount = skippedCount;
            this.noOp = noOp;
            this.reason = reason;
        }

        public String getMode() {
            return mode;
        }

        public int getAssetCount() {
            return assetCount;
        }

        public int getCandidateCount() {
            return candidateCount;
        }

        public int getCopiedCount() {
            return copiedCount;
        }

        public int getSkippedCount() {
            return skippedCount;
        }

        public boolean isNoOp() {
            return noOp;
        }

        public String getReason() {
            return reason;
        }
    }
}
