package com.homeworkgrader.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.dto.RubricCompileRequest;
import com.homeworkgrader.dto.RubricCompileResponse;
import com.homeworkgrader.service.llm.LlmClient;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
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
        Map<String, Object> rubricJson = parseRubricJson(rawContent);
        RubricJsonValidator.ValidationResult validation = validator.validate(rubricJson, request.getTotalScore());
        return toResponse(rubricJson, validation);
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
                + "5. 如果教师描述中的分值之和与任务总分不一致，不要强行修正，在 warnings 中说明。\n"
                + "6. 如果缺少档位描述，可以生成默认 excellent / qualified / weak 三档，但要在 warnings 中说明。\n"
                + "7. cap_rules 用于表达“最高不超过多少分”“最多多少分”等封顶规则。\n"
                + "8. review_flags 用于表达“需要人工复核”“证据矛盾”“难以判断”等风险规则。\n"
                + "9. 输出必须是合法 JSON。\n"
                + "10. 不允许输出代码块标记。\n"
                + "11. 不允许输出任何 JSON 以外的文字。";
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
        response.setWarnings(mergeWarnings(list(rubricJson.get("warnings")), validation));
        response.setCanSave(validation.isCanSave());
        response.setRubricJson(rubricJson);
        return response;
    }

    private List<RubricCompileResponse.Dimension> mapDimensions(List<?> items) {
        if (items == null) {
            return Collections.emptyList();
        }
        List<RubricCompileResponse.Dimension> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) {
                continue;
            }
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
        if (items == null) {
            return Collections.emptyList();
        }
        List<RubricCompileResponse.Level> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) {
                continue;
            }
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
        if (items == null) {
            return Collections.emptyList();
        }
        List<RubricCompileResponse.DeductionRule> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) {
                continue;
            }
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.DeductionRule rule = new RubricCompileResponse.DeductionRule();
            rule.setCondition(text(map.get("condition")));
            rule.setDeduct(decimal(map.get("deduct")));
            result.add(rule);
        }
        return result;
    }

    private List<RubricCompileResponse.CapRule> mapCapRules(List<?> items) {
        if (items == null) {
            return Collections.emptyList();
        }
        List<RubricCompileResponse.CapRule> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) {
                continue;
            }
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
        if (items == null) {
            return Collections.emptyList();
        }
        List<RubricCompileResponse.ReviewFlag> result = new ArrayList<>();
        for (Object item : items) {
            if (!(item instanceof Map)) {
                continue;
            }
            Map<?, ?> map = (Map<?, ?>) item;
            RubricCompileResponse.ReviewFlag flag = new RubricCompileResponse.ReviewFlag();
            flag.setCondition(text(map.get("condition")));
            flag.setAction(text(map.get("action")));
            result.add(flag);
        }
        return result;
    }

    private List<String> mergeWarnings(List<?> modelWarnings, RubricJsonValidator.ValidationResult validation) {
        List<String> result = new ArrayList<>();
        result.addAll(stringList(modelWarnings));
        result.addAll(validation.getWarnings());
        result.addAll(validation.getErrors());
        return result;
    }

    private List<String> stringList(List<?> items) {
        if (items == null) {
            return Collections.emptyList();
        }
        List<String> result = new ArrayList<>();
        for (Object item : items) {
            String value = text(item);
            if (!value.isEmpty()) {
                result.add(value);
            }
        }
        return result;
    }

    private List<BigDecimal> decimalList(List<?> items) {
        if (items == null) {
            return Collections.emptyList();
        }
        List<BigDecimal> result = new ArrayList<>();
        for (Object item : items) {
            BigDecimal value = decimal(item);
            if (value != null) {
                result.add(value);
            }
        }
        return result;
    }

    private List<?> list(Object value) {
        return value instanceof List ? (List<?>) value : null;
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String blankToDefault(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
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
}
