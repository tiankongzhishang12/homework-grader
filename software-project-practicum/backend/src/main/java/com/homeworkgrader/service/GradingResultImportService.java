package com.homeworkgrader.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.config.GraderProperties;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.BufferedReader;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class GradingResultImportService {
    private final CrudJdbcRepository repository;
    private final ObjectMapper objectMapper;
    private final Path workspaceRoot;

    public GradingResultImportService(CrudJdbcRepository repository, ObjectMapper objectMapper, GraderProperties properties) {
        this.repository = repository;
        this.objectMapper = objectMapper;
        this.workspaceRoot = properties.getWorkspaceRoot().toAbsolutePath().normalize();
    }

    public ImportSummary importScores(Long assessmentId) {
        ImportSummary summary = new ImportSummary();
        Map<String, String> studentNumbers = loadStudentMapping(summary);
        Path scoresRoot = workspaceRoot.resolve("scores").normalize();
        if (!Files.isDirectory(scoresRoot)) {
            summary.addSkipped("scores directory not found: " + scoresRoot);
            return summary;
        }

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(scoresRoot, "*.json")) {
            for (Path scorePath : stream) {
                importOne(assessmentId, scorePath, studentNumbers, summary);
            }
        } catch (IOException ex) {
            summary.addFailed("failed to scan scores directory: " + ex.getMessage());
        }
        return summary;
    }

    private void importOne(Long assessmentId, Path scorePath, Map<String, String> studentNumbers, ImportSummary summary) {
        try {
            Map<String, Object> score = readJson(scorePath);
            String anonymousId = asText(score.get("student_id"));
            if (isBlank(anonymousId)) {
                anonymousId = fileStem(scorePath);
            }

            String studentNo = studentNumbers.get(anonymousId);
            if (isBlank(studentNo)) {
                summary.addSkipped(scorePath.getFileName() + ": no student mapping for " + anonymousId);
                return;
            }

            Long studentId = findStudentId(studentNo);
            if (studentId == null) {
                summary.addSkipped(scorePath.getFileName() + ": no student for student_no " + studentNo);
                return;
            }

            Long submissionId = findLatestSubmissionId(assessmentId, studentId);
            if (submissionId == null) {
                summary.addSkipped(scorePath.getFileName() + ": no submission for assessment " + assessmentId + " and student " + studentId);
                return;
            }

            Long gradingRunId = insertGradingRun(submissionId, score);
            insertScoreItems(gradingRunId, score);
            upsertFinalResult(submissionId, gradingRunId, score);
            summary.addImported(scorePath.getFileName().toString());
        } catch (Exception ex) {
            summary.addFailed(scorePath.getFileName() + ": " + ex.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readJson(Path path) throws IOException {
        return objectMapper.readValue(path.toFile(), Map.class);
    }

    private Map<String, String> loadStudentMapping(ImportSummary summary) {
        Map<String, String> mapping = new HashMap<>();
        Path mappingPath = workspaceRoot.resolve("student-mapping.csv").normalize();
        if (!Files.exists(mappingPath)) {
            summary.addSkipped("student-mapping.csv not found: " + mappingPath);
            return mapping;
        }

        try (BufferedReader reader = Files.newBufferedReader(mappingPath, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                summary.addSkipped("student-mapping.csv is empty");
                return mapping;
            }
            List<String> headers = parseCsvLine(headerLine);
            if (!headers.isEmpty()) {
                headers.set(0, headers.get(0).replace("\uFEFF", ""));
            }
            int anonIndex = headers.indexOf("anon_id");
            int numberIndex = headers.indexOf("student_number");
            if (anonIndex < 0 || numberIndex < 0) {
                summary.addSkipped("student-mapping.csv missing anon_id or student_number header");
                return mapping;
            }
            String line;
            while ((line = reader.readLine()) != null) {
                List<String> columns = parseCsvLine(line);
                if (columns.size() > Math.max(anonIndex, numberIndex)) {
                    String anonId = columns.get(anonIndex).trim();
                    String studentNo = columns.get(numberIndex).trim();
                    if (!isBlank(anonId) && !isBlank(studentNo)) {
                        mapping.put(anonId, studentNo);
                    }
                }
            }
        } catch (IOException ex) {
            summary.addFailed("failed to read student-mapping.csv: " + ex.getMessage());
        }
        return mapping;
    }

    private List<String> parseCsvLine(String line) {
        List<String> values = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (ch == '"') {
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else {
                    quoted = !quoted;
                }
            } else if (ch == ',' && !quoted) {
                values.add(current.toString());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }
        values.add(current.toString());
        return values;
    }

    private Long findStudentId(String studentNo) {
        List<Map<String, Object>> rows = repository.query(
                "select id from student where student_no = :studentNo and status = 1 order by id desc limit 1",
                Maps.of("studentNo", studentNo)
        );
        return firstLong(rows, "id");
    }

    private Long findLatestSubmissionId(Long assessmentId, Long studentId) {
        List<Map<String, Object>> rows = repository.query(
                "select id from submission where assessment_id = :assessmentId and student_id = :studentId order by attempt_no desc, id desc limit 1",
                Maps.of("assessmentId", assessmentId, "studentId", studentId)
        );
        return firstLong(rows, "id");
    }

    private Long insertGradingRun(Long submissionId, Map<String, Object> score) {
        Map<String, Object> values = new HashMap<>();
        values.put("submission_id", submissionId);
        values.put("extraction_run_id", null);
        values.put("run_type", "AI_BATCH");
        values.put("grading_mode", "AUTO");
        values.put("model_name", modelName(score));
        values.put("rubric_version", asText(score.get("rubric_id")));
        values.put("total_score", scoreValue(score));
        values.put("confidence", decimal(score.get("overall_confidence")));
        values.put("status", "COMPLETED");
        return repository.insert("grading_run", values);
    }

    @SuppressWarnings("unchecked")
    private void insertScoreItems(Long gradingRunId, Map<String, Object> score) throws IOException {
        Object dimensionsValue = score.get("dimension_scores");
        if (!(dimensionsValue instanceof List)) {
            return;
        }
        String reviewFlag = normalizedReviewFlag(score);
        List<Object> dimensions = (List<Object>) dimensionsValue;
        for (Object value : dimensions) {
            if (!(value instanceof Map)) {
                continue;
            }
            Map<String, Object> dimension = (Map<String, Object>) value;
            Map<String, Object> item = new HashMap<>();
            BigDecimal confidence = decimal(dimension.get("confidence"));
            item.put("grading_run_id", gradingRunId);
            item.put("item_type", "RUBRIC");
            item.put("question_definition_id", null);
            item.put("rubric_definition_id", null);
            item.put("score", decimalOrZero(dimension.get("score")));
            item.put("max_score", maxScore(dimension));
            item.put("is_correct", null);
            item.put("needs_review", needsReview(confidence, reviewFlag) ? 1 : 0);
            item.put("confidence", confidence);
            item.put("evidence_text", asText(dimension.get("evidence")));
            item.put("evidence_json", objectMapper.writeValueAsString(dimension));
            item.put("comment_text", commentText(dimension));
            repository.insert("score_item_result", item);
        }
    }

    private void upsertFinalResult(Long submissionId, Long gradingRunId, Map<String, Object> score) {
        Map<String, Object> values = new HashMap<>();
        values.put("selected_grading_run_id", gradingRunId);
        values.put("final_score", scoreValue(score));
        values.put("score_source", "AI");
        values.put("review_status", "none".equals(normalizedReviewFlag(score)) ? "AI_GENERATED" : "NEEDS_REVIEW");
        values.put("confirmed_by_teacher_id", null);
        values.put("confirmed_at", null);

        List<Map<String, Object>> existing = repository.query(
                "select id from final_result where submission_id = :submissionId limit 1",
                Maps.of("submissionId", submissionId)
        );
        Long existingId = firstLong(existing, "id");
        if (existingId == null) {
            values.put("submission_id", submissionId);
            repository.insert("final_result", values);
        } else {
            repository.update("final_result", existingId, values);
        }
    }

    @SuppressWarnings("unchecked")
    private String modelName(Map<String, Object> score) {
        Object metadataValue = score.get("metadata");
        if (metadataValue instanceof Map) {
            Object model = ((Map<String, Object>) metadataValue).get("model_name");
            if (!isBlank(asText(model))) {
                return asText(model);
            }
        }
        return "PYTHON_SCRIPT";
    }

    private BigDecimal scoreValue(Map<String, Object> score) {
        BigDecimal raw = decimal(score.get("raw_total_score"));
        if (raw != null) {
            return raw;
        }
        BigDecimal percentile = decimal(score.get("percentile_score"));
        return percentile == null ? BigDecimal.ZERO : percentile;
    }

    private BigDecimal maxScore(Map<String, Object> dimension) {
        BigDecimal max = decimal(dimension.get("max_score"));
        if (max != null) {
            return max;
        }
        max = decimal(dimension.get("maxScore"));
        return max == null ? BigDecimal.ZERO : max;
    }

    private boolean needsReview(BigDecimal confidence, String reviewFlag) {
        if (!"none".equals(reviewFlag)) {
            return true;
        }
        return confidence != null && confidence.compareTo(new BigDecimal("0.7")) < 0;
    }

    private String normalizedReviewFlag(Map<String, Object> score) {
        String flag = asText(score.get("review_flag"));
        return isBlank(flag) ? "none" : flag.trim().toLowerCase();
    }

    private String commentText(Map<String, Object> dimension) {
        String improvement = asText(dimension.get("improvement"));
        if (!isBlank(improvement)) {
            return improvement;
        }
        return asText(dimension.get("reasoning"));
    }

    private BigDecimal decimalOrZero(Object value) {
        BigDecimal decimal = decimal(value);
        return decimal == null ? BigDecimal.ZERO : decimal;
    }

    private BigDecimal decimal(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof BigDecimal) {
            return (BigDecimal) value;
        }
        if (value instanceof Number) {
            return BigDecimal.valueOf(((Number) value).doubleValue());
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty()) {
            return null;
        }
        return new BigDecimal(text);
    }

    private Long firstLong(List<Map<String, Object>> rows, String column) {
        if (rows == null || rows.isEmpty()) {
            return null;
        }
        Object value = rows.get(0).get(column);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return value == null ? null : Long.valueOf(String.valueOf(value));
    }

    private String asText(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String fileStem(Path path) {
        String name = path.getFileName().toString();
        int dot = name.lastIndexOf('.');
        return dot < 0 ? name : name.substring(0, dot);
    }

    public static class ImportSummary {
        private int importedCount;
        private int skippedCount;
        private int failedCount;
        private final List<String> imported = new ArrayList<>();
        private final List<String> skipped = new ArrayList<>();
        private final List<String> failed = new ArrayList<>();

        void addImported(String item) {
            importedCount++;
            imported.add(item);
        }

        void addSkipped(String item) {
            skippedCount++;
            skipped.add(item);
        }

        void addFailed(String item) {
            failedCount++;
            failed.add(item);
        }

        public int getImportedCount() {
            return importedCount;
        }

        public int getSkippedCount() {
            return skippedCount;
        }

        public int getFailedCount() {
            return failedCount;
        }

        public List<String> getImported() {
            return imported;
        }

        public List<String> getSkipped() {
            return skipped;
        }

        public List<String> getFailed() {
            return failed;
        }
    }
}
