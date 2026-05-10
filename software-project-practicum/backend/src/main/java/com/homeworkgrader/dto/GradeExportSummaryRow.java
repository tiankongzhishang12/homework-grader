package com.homeworkgrader.dto;

import java.math.BigDecimal;

public class GradeExportSummaryRow {
    private String studentNo;
    private String studentName;
    private Long submissionId;
    private Long finalResultId;
    private BigDecimal finalScore;
    private String scoreSource;
    private String reviewStatus;
    private String confirmedAt;
    private BigDecimal confidence;
    private String gradingRunStatus;
    private String modelName;

    public String getStudentNo() { return studentNo; }
    public void setStudentNo(String studentNo) { this.studentNo = studentNo; }
    public String getStudentName() { return studentName; }
    public void setStudentName(String studentName) { this.studentName = studentName; }
    public Long getSubmissionId() { return submissionId; }
    public void setSubmissionId(Long submissionId) { this.submissionId = submissionId; }
    public Long getFinalResultId() { return finalResultId; }
    public void setFinalResultId(Long finalResultId) { this.finalResultId = finalResultId; }
    public BigDecimal getFinalScore() { return finalScore; }
    public void setFinalScore(BigDecimal finalScore) { this.finalScore = finalScore; }
    public String getScoreSource() { return scoreSource; }
    public void setScoreSource(String scoreSource) { this.scoreSource = scoreSource; }
    public String getReviewStatus() { return reviewStatus; }
    public void setReviewStatus(String reviewStatus) { this.reviewStatus = reviewStatus; }
    public String getConfirmedAt() { return confirmedAt; }
    public void setConfirmedAt(String confirmedAt) { this.confirmedAt = confirmedAt; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public String getGradingRunStatus() { return gradingRunStatus; }
    public void setGradingRunStatus(String gradingRunStatus) { this.gradingRunStatus = gradingRunStatus; }
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }
}
