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
            errors.add("dimensions 必须为非空数组。");
        } else {
            BigDecimal sum = BigDecimal.ZERO;
            for (int i = 0; i < dimensions.size(); i++) {
                Object raw = dimensions.get(i);
                if (!(raw instanceof Map)) {
                    errors.add("dimensions[" + i + "] 必须为对象。");
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
                errors.add("评分维度总分 " + sum + " 与 total_score " + totalScore + " 不一致。");
                warnings.add("维度分值之和与任务总分不一致，请调整后重新生成。");
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
        if (isBlank(text(dimension.get("code")))) {
            errors.add("dimensions[" + index + "] 缺少 code。");
        }
        if (isBlank(text(dimension.get("name")))) {
            errors.add("dimensions[" + index + "] 缺少 name。");
        }
        if (isBlank(text(dimension.get("description")))) {
            errors.add("dimensions[" + index + "] 缺少 description。");
        }
        BigDecimal maxScore = decimal(dimension.get("max_score"));
        if (maxScore == null || maxScore.compareTo(BigDecimal.ZERO) <= 0) {
            errors.add("dimensions[" + index + "].max_score 必须为正数。");
        }
        if (list(dimension.get("evidence_requirements")) == null) {
            errors.add("dimensions[" + index + "] 缺少 evidence_requirements 字段。");
        }
        List<?> levels = list(dimension.get("levels"));
        if (levels == null) {
            errors.add("dimensions[" + index + "] 缺少 levels 字段。");
        } else if (levels.isEmpty()) {
            warnings.add("评分项 " + text(dimension.get("name")) + " 未提供档位细节，请教师确认。");
        } else {
            for (int i = 0; i < levels.size(); i++) {
                validateLevel(levels.get(i), index, i, maxScore, errors);
            }
        }
        if (list(dimension.get("deduction_rules")) == null) {
            errors.add("dimensions[" + index + "] 缺少 deduction_rules 字段。");
        }
    }

    private void validateLevel(Object raw, int dimensionIndex, int levelIndex, BigDecimal maxScore, List<String> errors) {
        if (!(raw instanceof Map)) {
            errors.add("dimensions[" + dimensionIndex + "].levels[" + levelIndex + "] 必须为对象。");
            return;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> level = (Map<String, Object>) raw;
        List<?> range = list(level.get("score_range"));
        if (range == null || range.size() != 2) {
            errors.add("dimensions[" + dimensionIndex + "].levels[" + levelIndex + "].score_range 必须包含两个数字。");
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
            errors.add("cap_rules 字段必须存在，可以为空数组。");
            return;
        }
        if (!capRules.isEmpty()) {
            warnings.add("草稿包含封顶规则，请教师确认。");
        }
        for (Object item : capRules) {
            if (item instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> rule = (Map<String, Object>) item;
                BigDecimal capScore = decimal(rule.get("cap_score"));
                if (capScore != null && totalScore != null && capScore.compareTo(totalScore) > 0) {
                    errors.add("cap_rules.cap_score 不得大于 total_score。");
                }
            }
        }
    }

    private void validateReviewFlags(Object raw, List<String> errors, List<String> warnings) {
        List<?> reviewFlags = list(raw);
        if (reviewFlags == null) {
            errors.add("review_flags 字段必须存在，可以为空数组。");
            return;
        }
        if (!reviewFlags.isEmpty()) {
            warnings.add("草稿包含人工复核规则，请教师确认。");
        }
        for (Object item : reviewFlags) {
            if (item instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> flag = (Map<String, Object>) item;
                String action = text(flag.get("action"));
                if (!"manual_review".equals(action)) {
                    errors.add("review_flags.action 只允许 manual_review。");
                }
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
