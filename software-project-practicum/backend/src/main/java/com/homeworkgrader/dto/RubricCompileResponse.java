package com.homeworkgrader.dto;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public class RubricCompileResponse {
    private String rubricName;
    private BigDecimal totalScore;
    private List<Dimension> dimensions;
    private List<CapRule> capRules;
    private List<ReviewFlag> reviewFlags;
    private List<String> warnings;
    private boolean canSave;
    private Map<String, Object> rubricJson;

    public String getRubricName() { return rubricName; }
    public void setRubricName(String rubricName) { this.rubricName = rubricName; }
    public BigDecimal getTotalScore() { return totalScore; }
    public void setTotalScore(BigDecimal totalScore) { this.totalScore = totalScore; }
    public List<Dimension> getDimensions() { return dimensions; }
    public void setDimensions(List<Dimension> dimensions) { this.dimensions = dimensions; }
    public List<CapRule> getCapRules() { return capRules; }
    public void setCapRules(List<CapRule> capRules) { this.capRules = capRules; }
    public List<ReviewFlag> getReviewFlags() { return reviewFlags; }
    public void setReviewFlags(List<ReviewFlag> reviewFlags) { this.reviewFlags = reviewFlags; }
    public List<String> getWarnings() { return warnings; }
    public void setWarnings(List<String> warnings) { this.warnings = warnings; }
    public boolean isCanSave() { return canSave; }
    public void setCanSave(boolean canSave) { this.canSave = canSave; }
    public Map<String, Object> getRubricJson() { return rubricJson; }
    public void setRubricJson(Map<String, Object> rubricJson) { this.rubricJson = rubricJson; }

    public static class Dimension {
        private String code;
        private String name;
        private BigDecimal maxScore;
        private String description;
        private List<String> evidenceRequirements;
        private List<Level> levels;
        private List<DeductionRule> deductionRules;

        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public BigDecimal getMaxScore() { return maxScore; }
        public void setMaxScore(BigDecimal maxScore) { this.maxScore = maxScore; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public List<String> getEvidenceRequirements() { return evidenceRequirements; }
        public void setEvidenceRequirements(List<String> evidenceRequirements) { this.evidenceRequirements = evidenceRequirements; }
        public List<Level> getLevels() { return levels; }
        public void setLevels(List<Level> levels) { this.levels = levels; }
        public List<DeductionRule> getDeductionRules() { return deductionRules; }
        public void setDeductionRules(List<DeductionRule> deductionRules) { this.deductionRules = deductionRules; }
    }

    public static class Level {
        private String level;
        private List<BigDecimal> scoreRange;
        private String description;

        public String getLevel() { return level; }
        public void setLevel(String level) { this.level = level; }
        public List<BigDecimal> getScoreRange() { return scoreRange; }
        public void setScoreRange(List<BigDecimal> scoreRange) { this.scoreRange = scoreRange; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
    }

    public static class DeductionRule {
        private String condition;
        private BigDecimal deduct;

        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }
        public BigDecimal getDeduct() { return deduct; }
        public void setDeduct(BigDecimal deduct) { this.deduct = deduct; }
    }

    public static class CapRule {
        private String condition;
        private BigDecimal capScore;
        private String reason;

        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }
        public BigDecimal getCapScore() { return capScore; }
        public void setCapScore(BigDecimal capScore) { this.capScore = capScore; }
        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
    }

    public static class ReviewFlag {
        private String condition;
        private String action;

        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }
        public String getAction() { return action; }
        public void setAction(String action) { this.action = action; }
    }
}
