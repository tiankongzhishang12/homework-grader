package com.homeworkgrader.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.config.GraderProperties;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class RubricRuntimeExportService {
    private final CrudJdbcRepository repository;
    private final ObjectMapper objectMapper;
    private final Path workspaceRoot;

    public RubricRuntimeExportService(CrudJdbcRepository repository, ObjectMapper objectMapper, GraderProperties properties) {
        this.repository = repository;
        this.objectMapper = objectMapper;
        this.workspaceRoot = properties.getWorkspaceRoot().toAbsolutePath().normalize();
    }

    public RuntimeRubric exportForAssessment(Long assessmentId) {
        Map<String, Object> template = findTemplate(assessmentId);
        Long templateId = longValue(template.get("id"));
        Map<String, Object> rubric = findRubric(templateId);
        Long rubricDefinitionId = longValue(rubric.get("id"));
        String rawJson = text(rubric.get("deduction_rule"));
        if (isBlank(rawJson)) {
            throw new IllegalStateException("当前评分标准内容为空或不是合法 JSON，请重新生成 Rubric。");
        }

        Map<String, Object> rubricJson = parseRubricJson(rawJson);
        String rubricRuntimeId = "db-rubric-" + rubricDefinitionId;
        String rubricName = firstNonBlank(text(rubricJson.get("rubric_name")), text(rubric.get("rubric_name")));
        String yaml = toRuntimeYaml(rubricDefinitionId, rubricRuntimeId, rubricName, rubricJson);
        Path path = workspaceRoot.resolve("runtime/rubrics/assessment-" + assessmentId + "-rubric.yaml").normalize();
        ensureInsideWorkspace(path);
        try {
            Files.createDirectories(path.getParent());
            Files.write(path, yaml.getBytes(StandardCharsets.UTF_8));
        } catch (IOException ex) {
            throw new IllegalStateException("运行时 Rubric 文件生成失败，请检查工作区权限。", ex);
        }
        return new RuntimeRubric(rubricDefinitionId, path, rubricRuntimeId, rubricName);
    }

    private Map<String, Object> findTemplate(Long assessmentId) {
        List<Map<String, Object>> rows = repository.query(
                "select id from assessment_template where assessment_id = :assessmentId order by is_active desc, version_no desc, id desc limit 1",
                Maps.of("assessmentId", assessmentId)
        );
        if (rows.isEmpty()) {
            throw new IllegalStateException("当前考核尚未配置 assessment template，请先完成任务配置。");
        }
        return rows.get(0);
    }

    private Map<String, Object> findRubric(Long templateId) {
        List<Map<String, Object>> rows = repository.query(
                "select id, rubric_code, rubric_name, max_score, description, deduction_rule from rubric_definition where template_id = :templateId order by id desc limit 1",
                Maps.of("templateId", templateId)
        );
        if (rows.isEmpty()) {
            throw new IllegalStateException("当前考核尚未保存评分标准，请先生成并保存 Rubric。");
        }
        return rows.get(0);
    }

    private Map<String, Object> parseRubricJson(String rawJson) {
        try {
            return objectMapper.readValue(rawJson, new TypeReference<Map<String, Object>>() {});
        } catch (Exception ex) {
            throw new IllegalStateException("当前评分标准不是合法 JSON，请重新生成 Rubric。", ex);
        }
    }

    private String toRuntimeYaml(Long rubricDefinitionId, String runtimeId, String rubricName, Map<String, Object> rubricJson) {
        BigDecimal totalScore = decimal(rubricJson.get("total_score"));
        List<?> dimensions = list(rubricJson.get("dimensions"));
        if (totalScore == null || totalScore.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalStateException("当前评分标准缺少合法总分，无法开始评分。");
        }
        if (dimensions == null || dimensions.isEmpty()) {
            throw new IllegalStateException("当前评分标准缺少评分维度，无法开始评分。");
        }

        BigDecimal sum = BigDecimal.ZERO;
        StringBuilder yaml = new StringBuilder();
        yaml.append("rubric:\n");
        appendScalar(yaml, 2, "id", runtimeId);
        appendScalar(yaml, 2, "name", rubricName);
        yaml.append("  version: 1.0\n");
        appendScalar(yaml, 2, "description", "由教师中文描述经大模型生成，并由教师确认保存。");
        appendBlock(yaml, 2, "instruction", buildInstruction(rubricJson));
        appendScalar(yaml, 2, "score_mode", "raw");
        yaml.append("  max_total_score: ").append(strip(totalScore)).append("\n");
        yaml.append("  criteria:\n");

        for (int i = 0; i < dimensions.size(); i++) {
            Object raw = dimensions.get(i);
            if (!(raw instanceof Map)) {
                throw new IllegalStateException("当前评分标准维度格式非法，无法开始评分。");
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> dimension = (Map<String, Object>) raw;
            BigDecimal maxScore = decimal(dimension.get("max_score"));
            if (maxScore == null || maxScore.compareTo(BigDecimal.ZERO) <= 0) {
                throw new IllegalStateException("当前评分标准维度分值非法，无法开始评分。");
            }
            sum = sum.add(maxScore);
            String code = safeCode(text(dimension.get("code")), i + 1);
            yaml.append("    ").append(code).append(":\n");
            appendScalar(yaml, 6, "name", firstNonBlank(text(dimension.get("name")), code));
            yaml.append("      max_score: ").append(strip(maxScore)).append("\n");
            appendScalar(yaml, 6, "description", text(dimension.get("description")));
            appendBlock(yaml, 6, "scoring_guidance", buildScoringGuidance(dimension));
            appendScalar(yaml, 6, "evidence_type", "observation");
            appendScalar(yaml, 6, "evidence_source", "text");
            yaml.append("      deduction_rules:\n");
            List<String> deductionRules = deductionRuleTexts(list(dimension.get("deduction_rules")));
            if (deductionRules.isEmpty()) {
                yaml.append("        []\n");
            } else {
                for (String rule : deductionRules) {
                    appendListItem(yaml, 8, rule);
                }
            }
        }
        if (sum.compareTo(totalScore) != 0) {
            throw new IllegalStateException("当前评分标准维度总分与任务总分不一致，无法开始评分。");
        }

        yaml.append("  thresholds:\n");
        yaml.append("    accept: 85\n");
        yaml.append("    reject: 60\n");
        yaml.append("    review:\n");
        yaml.append("      - 60\n");
        yaml.append("      - 85\n");
        yaml.append("  comment_guidelines:\n");
        appendScalar(yaml, 4, "tone", "constructive, specific");
        appendScalar(yaml, 4, "language", "zh-CN");
        yaml.append("    length_range:\n");
        yaml.append("      - 200\n");
        yaml.append("      - 400\n");
        yaml.append("    required_sections:\n");
        yaml.append("      - strengths\n");
        yaml.append("      - weaknesses\n");
        yaml.append("      - suggestions\n");
        yaml.append("    prohibited_patterns: []\n");
        return yaml.toString();
    }

    private String buildInstruction(Map<String, Object> rubricJson) {
        StringBuilder text = new StringBuilder();
        text.append("请严格按照以下 Rubric 对学生作业进行评分。\n\n");
        text.append("全局封顶规则：\n");
        List<?> capRules = list(rubricJson.get("cap_rules"));
        if (capRules == null || capRules.isEmpty()) {
            text.append("- 无\n");
        } else {
            for (Object item : capRules) {
                if (item instanceof Map) {
                    Map<?, ?> rule = (Map<?, ?>) item;
                    text.append("- 如果 ").append(text(rule.get("condition"))).append("，则最高不超过 ")
                            .append(text(rule.get("cap_score"))).append(" 分。");
                    if (!isBlank(text(rule.get("reason")))) {
                        text.append("原因：").append(text(rule.get("reason")));
                    }
                    text.append("\n");
                }
            }
        }
        text.append("\n人工复核规则：\n");
        List<?> reviewFlags = list(rubricJson.get("review_flags"));
        if (reviewFlags == null || reviewFlags.isEmpty()) {
            text.append("- 无\n");
        } else {
            for (Object item : reviewFlags) {
                if (item instanceof Map) {
                    Map<?, ?> flag = (Map<?, ?>) item;
                    text.append("- 如果 ").append(text(flag.get("condition"))).append("，则标记为 ")
                            .append(text(flag.get("action"))).append("。\n");
                }
            }
        }
        return text.toString();
    }

    private String buildScoringGuidance(Map<String, Object> dimension) {
        StringBuilder text = new StringBuilder();
        text.append("证据要求：\n");
        List<String> evidence = stringList(list(dimension.get("evidence_requirements")));
        if (evidence.isEmpty()) {
            text.append("- 未明确，请根据评分项描述判断。\n");
        } else {
            for (String item : evidence) {
                text.append("- ").append(item).append("\n");
            }
        }
        text.append("\n档位描述：\n");
        List<?> levels = list(dimension.get("levels"));
        if (levels == null || levels.isEmpty()) {
            text.append("- 未明确，请按得分区间和证据充分程度判断。\n");
        } else {
            for (Object item : levels) {
                if (item instanceof Map) {
                    Map<?, ?> level = (Map<?, ?>) item;
                    text.append("- ").append(text(level.get("level"))).append(": ");
                    List<?> range = list(level.get("score_range"));
                    if (range != null && range.size() == 2) {
                        text.append(text(range.get(0))).append("-").append(text(range.get(1))).append(" 分，");
                    }
                    text.append(text(level.get("description"))).append("\n");
                }
            }
        }
        text.append("\n扣分规则：\n");
        List<String> rules = deductionRuleTexts(list(dimension.get("deduction_rules")));
        if (rules.isEmpty()) {
            text.append("- 无\n");
        } else {
            for (String rule : rules) {
                text.append("- ").append(rule).append("\n");
            }
        }
        return text.toString();
    }

    private List<String> deductionRuleTexts(List<?> rules) {
        List<String> result = new ArrayList<>();
        if (rules == null) {
            return result;
        }
        for (Object item : rules) {
            if (item instanceof Map) {
                Map<?, ?> rule = (Map<?, ?>) item;
                String line = text(rule.get("condition"));
                if (!isBlank(text(rule.get("deduct")))) {
                    line = line + "，扣 " + text(rule.get("deduct")) + " 分";
                }
                if (!isBlank(line)) {
                    result.add(line);
                }
            } else if (!isBlank(text(item))) {
                result.add(text(item));
            }
        }
        return result;
    }

    private void appendScalar(StringBuilder yaml, int indent, String key, String value) {
        yaml.append(spaces(indent)).append(key).append(": ").append(quote(value)).append("\n");
    }

    private void appendBlock(StringBuilder yaml, int indent, String key, String value) {
        yaml.append(spaces(indent)).append(key).append(": |\n");
        String safe = value == null ? "" : value;
        String[] lines = safe.split("\\r?\\n", -1);
        for (String line : lines) {
            yaml.append(spaces(indent + 2)).append(line).append("\n");
        }
    }

    private void appendListItem(StringBuilder yaml, int indent, String value) {
        yaml.append(spaces(indent)).append("- ").append(quote(value)).append("\n");
    }

    private String quote(String value) {
        String safe = value == null ? "" : value;
        return "\"" + safe.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", "").replace("\n", " ") + "\"";
    }

    private String safeCode(String code, int index) {
        String value = isBlank(code) ? "criterion_" + index : code.trim();
        value = value.replaceAll("[^A-Za-z0-9_\\-]", "_");
        return isBlank(value) ? "criterion_" + index : value;
    }

    private List<String> stringList(List<?> items) {
        List<String> result = new ArrayList<>();
        if (items == null) {
            return result;
        }
        for (Object item : items) {
            if (!isBlank(text(item))) {
                result.add(text(item));
            }
        }
        return result;
    }

    private void ensureInsideWorkspace(Path path) {
        if (!path.startsWith(workspaceRoot)) {
            throw new IllegalStateException("运行时 Rubric 文件路径不在工作区内。");
        }
    }

    private List<?> list(Object value) {
        return value instanceof List ? (List<?>) value : null;
    }

    private BigDecimal decimal(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private Long longValue(Object value) {
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return value == null ? null : Long.valueOf(String.valueOf(value));
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String firstNonBlank(String first, String second) {
        return isBlank(first) ? second : first;
    }

    private String strip(BigDecimal value) {
        return value.stripTrailingZeros().toPlainString();
    }

    private String spaces(int count) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < count; i++) {
            builder.append(' ');
        }
        return builder.toString();
    }

    public static class RuntimeRubric {
        private final Long rubricDefinitionId;
        private final Path rubricYamlPath;
        private final String rubricRuntimeId;
        private final String rubricName;

        public RuntimeRubric(Long rubricDefinitionId, Path rubricYamlPath, String rubricRuntimeId, String rubricName) {
            this.rubricDefinitionId = rubricDefinitionId;
            this.rubricYamlPath = rubricYamlPath;
            this.rubricRuntimeId = rubricRuntimeId;
            this.rubricName = rubricName;
        }

        public Long getRubricDefinitionId() {
            return rubricDefinitionId;
        }

        public Path getRubricYamlPath() {
            return rubricYamlPath;
        }

        public String getRubricRuntimeId() {
            return rubricRuntimeId;
        }

        public String getRubricName() {
            return rubricName;
        }
    }
}
