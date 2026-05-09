package com.homeworkgrader.service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class RubricJsonValidator {
    public ValidationResult validate(Map<String, Object> rubric, BigDecimal expectedTotalScore) {
        List<String> warnings = new ArrayList<>();
        List<String> errors = new ArrayList<>();

        if (isBlank(text(rubric.get("rubric_name")))) {
            errors.add("缺少 rubric_name。");
        }
        BigDecimal totalScore = decimal(rubric.get("total_score"));
        if (totalScore == null || totalScore.compareTo(BigDecimal.ZERO) <= 0) {
            errors.add("total_score 必须为正数。");
        } else if (expectedTotalScore != null && totalScore.compareTo(expectedTotalScore) != 0) {
            errors.add("total_score 与任务总分不一致。");
        }

        List<?> dimensions = list(rubric.get("dimensions"));
        if (dimensions == null || dimensions.isEmpty()) {
            errors.add("当前评分标准缺少评分维度，无法保存。");
        } else {
            BigDecimal sum = BigDecimal.ZERO;
            for (int i = 0; i < dimensions.size(); i++) {
                Object raw = dimensions.get(i);
                if (!(raw instanceof Map)) {
                    errors.add("第 " + (i + 1) + " 个评分维度格式非法。");
                    continue;
                }
                @SuppressWarnings("unchecked")
                Map<String, Object> dimension = (Map<String, Object>) raw;
                validateDimension(dimension, i, errors, warnings);
                BigDecimal maxScore = decimal(dimension.get("max_score"));
                if (maxScore != null) {
                    sum = sum.add(maxScore);
                }
            }
            if (totalScore != null && sum.compareTo(totalScore) != 0) {
                errors.add("评分维度总分为 " + strip(sum) + "，与任务总分 " + strip(totalScore) + " 不一致。");
            }
        }

        validateCapRules(rubric.get("cap_rules"), totalScore, errors, warnings);
        validateReviewFlags(rubric.get("review_flags"), errors, warnings);
        if (list(rubric.get("warnings")) == null) {
            errors.add("warnings 字段必须存在，可以为空数组。");
        }

        return new ValidationResult(errors.isEmpty(), warnings, errors);
    }

    private void validateDimension(Map<String, Object> dimension, int index, List<String> errors, List<String> warnings) {
        int number = index + 1;
        if (isBlank(text(dimension.get("code")))) {
            errors.add("第 " + number + " 个评分维度缺少 code。");
        }
        if (isBlank(text(dimension.get("name")))) {
            errors.add("第 " + number + " 个评分维度缺少名称。");
        }
        if (isBlank(text(dimension.get("description")))) {
            errors.add("第 " + number + " 个评分维度缺少描述。");
        }
        BigDecimal maxScore = decimal(dimension.get("max_score"));
        if (maxScore == null || maxScore.compareTo(BigDecimal.ZERO) <= 0) {
            errors.add("第 " + number + " 个评分维度缺少合法 max_score。");
        }
        if (list(dimension.get("evidence_requirements")) == null) {
            errors.add("第 " + number + " 个评分维度缺少 evidence_requirements 字段。");
        }
        List<?> levels = list(dimension.get("levels"));
        if (levels == null) {
            errors.add("第 " + number + " 个评分维度缺少 levels 字段。");
        } else if (levels.isEmpty()) {
            warnings.add("评分项“" + text(dimension.get("name")) + "”未提供档位细节，请教师确认。");
        } else {
            for (int i = 0; i < levels.size(); i++) {
                validateLevel(levels.get(i), number, i + 1, maxScore, errors);
            }
        }
        if (list(dimension.get("deduction_rules")) == null) {
            errors.add("第 " + number + " 个评分维度缺少 deduction_rules 字段。");
        }
    }

    private void validateLevel(Object raw, int dimensionNumber, int levelNumber, BigDecimal maxScore, List<String> errors) {
        if (!(raw instanceof Map)) {
            errors.add("第 " + dimensionNumber + " 个评分维度的第 " + levelNumber + " 个档位格式非法。");
            return;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> level = (Map<String, Object>) raw;
        List<?> range = list(level.get("score_range"));
        if (range == null || range.size() != 2) {
            errors.add("第 " + dimensionNumber + " 个评分维度的第 " + levelNumber + " 个档位 score_range 必须包含两个数字。");
            return;
        }
        BigDecimal start = decimal(range.get(0));
        BigDecimal end = decimal(range.get(1));
        if (start == null || end == null) {
            errors.add("score_range 必须为数字。");
            return;
        }
        if (start.compareTo(BigDecimal.ZERO) < 0 || end.compareTo(BigDecimal.ZERO) < 0 || (maxScore != null && end.compareTo(maxScore) > 0)) {
            errors.add("score_range 必须在 0 到该评分项满分之间。");
        }
    }

    private void validateCapRules(Object raw, BigDecimal totalScore, List<String> errors, List<String> warnings) {
        List<?> capRules = list(raw);
        if (capRules == null) {
            errors.add("cap_rules 字段必须是数组。");
            return;
        }
        if (!capRules.isEmpty()) {
            warnings.add("草稿包含封顶规则，请教师确认。");
        }
        for (int i = 0; i < capRules.size(); i++) {
            Object item = capRules.get(i);
            if (!(item instanceof Map)) {
                errors.add("第 " + (i + 1) + " 条封顶规则格式非法。");
                continue;
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> rule = (Map<String, Object>) item;
            if (isBlank(text(rule.get("condition")))) {
                errors.add("第 " + (i + 1) + " 条封顶规则缺少触发条件。");
            }
            BigDecimal capScore = decimal(rule.get("cap_score"));
            if (capScore == null) {
                errors.add("第 " + (i + 1) + " 条封顶规则缺少合法 cap_score。");
            } else if (totalScore != null && capScore.compareTo(totalScore) > 0) {
                errors.add("第 " + (i + 1) + " 条封顶规则 cap_score 不能大于总分。");
            }
        }
    }

    private void validateReviewFlags(Object raw, List<String> errors, List<String> warnings) {
        List<?> reviewFlags = list(raw);
        if (reviewFlags == null) {
            errors.add("review_flags 字段必须是数组。");
            return;
        }
        if (!reviewFlags.isEmpty()) {
            warnings.add("草稿包含人工复核规则，请教师确认。");
        }
        for (int i = 0; i < reviewFlags.size(); i++) {
            Object item = reviewFlags.get(i);
            if (!(item instanceof Map)) {
                errors.add("第 " + (i + 1) + " 条人工复核规则格式非法。");
                continue;
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> flag = (Map<String, Object>) item;
            if (isBlank(text(flag.get("condition")))) {
                errors.add("第 " + (i + 1) + " 条人工复核规则缺少触发条件，请重新生成或补充 condition。");
            }
            String action = text(flag.get("action"));
            if (!"manual_review".equals(action)) {
                errors.add("第 " + (i + 1) + " 条人工复核规则 action 不合法，必须为 manual_review。");
            }
        }
    }

    private List<?> list(Object value) {
        return value instanceof List ? (List<?>) value : null;
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
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

    private String strip(BigDecimal value) {
        return value.stripTrailingZeros().toPlainString();
    }

    public static class ValidationResult {
        private final boolean canSave;
        private final List<String> warnings;
        private final List<String> errors;

        public ValidationResult(boolean canSave, List<String> warnings, List<String> errors) {
            this.canSave = canSave;
            this.warnings = warnings;
            this.errors = errors;
        }

        public boolean isCanSave() {
            return canSave;
        }

        public List<String> getWarnings() {
            return warnings;
        }

        public List<String> getErrors() {
            return errors;
        }
    }
}
