package com.homeworkgrader.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.dto.RubricCompileRequest;
import com.homeworkgrader.dto.RubricCompileResponse;
import com.homeworkgrader.service.llm.LlmClient;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class RubricCompilerService {
    private final LlmClient llmClient;
    private final RubricJsonValidator validator;
    private final ObjectMapper objectMapper;

    public RubricCompilerService(LlmClient llmClient, RubricJsonValidator validator, ObjectMapper objectMapper) {
        this.llmClient = llmClient;
        this.validator = validator;
        this.objectMapper = objectMapper;
    }

    public RubricCompileResponse compile(Long templateId, RubricCompileRequest request) {
        String rawContent = llmClient.generateJson(buildSystemPrompt(), buildUserPrompt(request));
        Map<String, Object> rubricJson = normalizeRubricJson(parseRubricJson(rawContent));
        RubricJsonValidator.ValidationResult validation = validator.validate(rubricJson, request.getTotalScore());
        return toResponse(rubricJson, validation);
    }

    private Map<String, Object> normalizeRubricJson(Map<String, Object> raw) {
        Map<String, Object> normalized = new LinkedHashMap<>(raw);
        normalized.put("warnings", list(raw.get("warnings")) == null ? new ArrayList<Object>() : new ArrayList<Object>(list(raw.get("warnings"))));
        normalized.put("dimensions", normalizeDimensions(list(raw.get("dimensions"))));
        normalized.put("cap_rules", normalizeCapRules(list(raw.get("cap_rules"))));
        normalized.put("review_flags", normalizeReviewFlags(list(raw.get("review_flags"))));
        return normalized;
    }

    private List<Map<String, Object>> normalizeDimensions(List<?> rawDimensions) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (rawDimensions == null) {
            return result;
        }
        Map<String, Integer> codeCounts = new HashMap<>();
        for (int i = 0; i < rawDimensions.size(); i++) {
            Object item = rawDimensions.get(i);
            if (!(item instanceof Map)) {
                continue;
            }
            Map<?, ?> source = (Map<?, ?>) item;
            Map<String, Object> dimension = new LinkedHashMap<>();
            String baseCode = safeCode(text(source.get("code")), i + 1);
            int count = codeCounts.containsKey(baseCode) ? codeCounts.get(baseCode) + 1 : 1;
            codeCounts.put(baseCode, count);
            String code = count == 1 ? baseCode : baseCode + "_" + count;
            dimension.put("code", code);
            dimension.put("name", text(source.get("name")));
            dimension.put("max_score", source.get("max_score"));
            dimension.put("description", text(source.get("description")));
            dimension.put("evidence_requirements", list(source.get("evidence_requirements")) == null ? new ArrayList<Object>() : new ArrayList<Object>(list(source.get("evidence_requirements"))));
            dimension.put("levels", list(source.get("levels")) == null ? new ArrayList<Object>() : new ArrayList<Object>(list(source.get("levels"))));
            dimension.put("deduction_rules", list(source.get("deduction_rules")) == null ? new ArrayList<Object>() : new ArrayList<Object>(list(source.get("deduction_rules"))));
            result.add(dimension);
        }
        return result;
    }

    private List<Map<String, Object>> normalizeCapRules(List<?> rawRules) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (rawRules == null) {
            return result;
        }
        for (Object item : rawRules) {
            if (!(item instanceof Map)) {
                continue;
            }
            Map<?, ?> source = (Map<?, ?>) item;
            Map<String, Object> rule = new LinkedHashMap<>();
            rule.put("condition", text(source.get("condition")));
            Object capScore = source.containsKey("cap_score") ? source.get("cap_score") : source.get("capScore");
            rule.put("cap_score", capScore);
            rule.put("reason", text(source.get("reason")));
            result.add(rule);
        }
        return result;
    }

    private List<Map<String, Object>> normalizeReviewFlags(List<?> rawFlags) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (rawFlags == null) {
            return result;
        }
        Set<String> seen = new LinkedHashSet<>();
        for (Object item : rawFlags) {
            if (!(item instanceof Map)) {
                continue;
            }
            Map<?, ?> source = (Map<?, ?>) item;
            String condition = text(source.get("condition"));
            String action = normalizeReviewAction(text(source.get("action")));
            String key = condition + "::" + action;
            if (seen.contains(key)) {
                continue;
            }
            seen.add(key);
            Map<String, Object> flag = new LinkedHashMap<>();
            flag.put("condition", condition);
            flag.put("action", action);
            result.add(flag);
        }
        return result;
    }

    private String normalizeReviewAction(String action) {
        String value = action == null ? "" : action.trim();
        String folded = value.toLowerCase().replace("-", "_").replace(" ", "_");
        Set<String> aliases = new HashSet<>();
        Collections.addAll(aliases,
                "manual_review", "manualreview", "review", "need_review", "needs_review", "human_review",
                "人工复核", "需要人工复核", "教师复核", "需要教师复核", "人工审核", "需要人工审核"
        );
        if (aliases.contains(value) || aliases.contains(folded)) {
            return "manual_review";
        }
        return value;
    }

    private String buildSystemPrompt() {
        return "你是智能阅卷系统中的 Rubric Compiler。\n"
                + "你的任务是把教师用中文描述的评分标准转换为严格 JSON。\n"
                + "你只能输出 JSON，不要输出 Markdown，不要输出解释性文字。\n\n"
                + "要求：\n"
                + "1. 必须保留教师原意，不要自行添加与任务无关的评分项。\n"
                + "2. 必须生成 rubric_name、total_score、dimensions、cap_rules、review_flags、warnings 字段。\n"
                + "3. dimensions 中每个评分项必须包含 code、name、max_score、description、evidence_requirements、levels、deduction_rules。\n"
                + "4. total_score 必须等于用户提供的任务总分。\n"
                + "5. review_flags.action 必须严格输出 manual_review。\n"
                + "6. review_flags.condition 不能为空。\n"
                + "7. cap_rules.cap_score 必须是数字。\n"
                + "8. 如果缺少档位描述，可以生成默认 excellent / qualified / weak 三档，但要在 warnings 中说明。\n"
                + "9. 输出必须是合法 JSON，不允许输出代码块标记。";
    }

    private String buildUserPrompt(RubricCompileRequest request) {
        return "任务名称：" + blankToDefault(request.getTaskName(), "未命名任务") + "\n"
                + "任务总分：" + request.getTotalScore() + "\n\n"
                + "教师原始评分标准描述如下：\n"
                + request.getTeacherText().trim() + "\n\n"
                + "请将以上中文评分标准转换为 Rubric JSON。";
    }

    private Map<String, Object> parseRubricJson(String rawContent) {
        if (rawContent == null || rawContent.trim().isEmpty()) {
            throw new IllegalStateException("模型返回空内容，无法生成 Rubric 草稿。");
        }
        String json = extractJsonObject(rawContent.trim());
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception ex) {
            throw new IllegalStateException("模型返回内容不是合法 JSON，无法生成 Rubric 草稿。", ex);
        }
    }

    private String extractJsonObject(String content) {
        int start = content.indexOf('{');
        int end = content.lastIndexOf('}');
        if (start < 0 || end <= start) {
            throw new IllegalStateException("模型返回内容不包含 JSON 对象。");
        }
        return content.substring(start, end + 1);
    }

    private RubricCompileResponse toResponse(Map<String, Object> rubricJson, RubricJsonValidator.ValidationResult validation) {
        RubricCompileResponse response = new RubricCompileResponse();
        response.setRubricName(text(rubricJson.get("rubric_name")));
        response.setTotalScore(decimal(rubricJson.get("total_score")));
        response.setDimensions(mapDimensions(list(rubricJson.get("dimensions"))));
        response.setCapRules(mapCapRules(list(rubricJson.get("cap_rules"))));
        response.setReviewFlags(mapReviewFlags(list(rubricJson.get("review_flags"))));
        response.setWarnings(mergeWarnings(list(rubricJson.get("warnings")), validation.getWarnings()));
        response.setErrors(validation.getErrors());
        response.setCanSave(validation.getErrors().isEmpty());
        response.setRubricJson(rubricJson);
        return response;
    }

    private List<RubricCompileResponse.Dimension> mapDimensions(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<RubricCompileResponse.Dimension> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) continue;
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.Dimension dimension = new RubricCompileResponse.Dimension();
            dimension.setCode(text(map.get("code")));
            dimension.setName(text(map.get("name")));
            dimension.setMaxScore(decimal(map.get("max_score")));
            dimension.setDescription(text(map.get("description")));
            dimension.setEvidenceRequirements(stringList(list(map.get("evidence_requirements"))));
            dimension.setLevels(mapLevels(list(map.get("levels"))));
            dimension.setDeductionRules(mapDeductionRules(list(map.get("deduction_rules"))));
            result.add(dimension);
        }
        return result;
    }

    private List<RubricCompileResponse.Level> mapLevels(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<RubricCompileResponse.Level> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) continue;
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.Level level = new RubricCompileResponse.Level();
            level.setLevel(text(map.get("level")));
            level.setScoreRange(decimalList(list(map.get("score_range"))));
            level.setDescription(text(map.get("description")));
            result.add(level);
        }
        return result;
    }

    private List<RubricCompileResponse.DeductionRule> mapDeductionRules(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<RubricCompileResponse.DeductionRule> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) continue;
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.DeductionRule rule = new RubricCompileResponse.DeductionRule();
            rule.setCondition(text(map.get("condition")));
            rule.setDeduct(decimal(map.get("deduct")));
            result.add(rule);
        }
        return result;
    }

    private List<RubricCompileResponse.CapRule> mapCapRules(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<RubricCompileResponse.CapRule> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) continue;
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.CapRule rule = new RubricCompileResponse.CapRule();
            rule.setCondition(text(map.get("condition")));
            rule.setCapScore(decimal(map.get("cap_score")));
            rule.setReason(text(map.get("reason")));
            result.add(rule);
        }
        return result;
    }

    private List<RubricCompileResponse.ReviewFlag> mapReviewFlags(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<RubricCompileResponse.ReviewFlag> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) continue;
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.ReviewFlag flag = new RubricCompileResponse.ReviewFlag();
            flag.setCondition(text(map.get("condition")));
            flag.setAction(text(map.get("action")));
            result.add(flag);
        }
        return result;
    }

    private List<String> mergeWarnings(List<?> modelWarnings, List<String> validatorWarnings) {
        List<String> result = new ArrayList<>();
        result.addAll(stringList(modelWarnings));
        result.addAll(validatorWarnings);
        return result;
    }

    private List<String> stringList(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<String> result = new ArrayList<>();
        for (Object item : items) {
            String value = text(item);
            if (!value.isEmpty()) result.add(value);
        }
        return result;
    }

    private List<BigDecimal> decimalList(List<?> items) {
        if (items == null) return Collections.emptyList();
        List<BigDecimal> result = new ArrayList<>();
        for (Object item : items) {
            BigDecimal value = decimal(item);
            if (value != null) result.add(value);
        }
        return result;
    }

    private List<?> list(Object value) {
        return value instanceof List ? (List<?>) value : null;
    }

    private String safeCode(String code, int index) {
        String value = code == null || code.trim().isEmpty() ? "criterion_" + index : code.trim();
        value = value.replaceAll("[^A-Za-z0-9_\\-]", "_");
        return value.trim().isEmpty() ? "criterion_" + index : value;
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String blankToDefault(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }

    private BigDecimal decimal(Object value) {
        if (value == null) return null;
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }
}
