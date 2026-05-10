package com.homeworkgrader.dto;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

public class StudentAnalysisDetailResponse {
    private String id;
    private String assessmentId;
    private String submissionId;
    private String finalResultId;
    private String studentId;
    private String name;
    private String studentNumber;
    private String anonymousId;
    private BigDecimal score;
    private BigDecimal percentileScore;
    private String grade;
    private BigDecimal confidence;
    private String reviewStatus;
    private Object confirmedAt;
    private String summary;
    private List<String> qualityFindings = new ArrayList<>();
    private List<StudentAnalysisDimensionResponse> dimensions = new ArrayList<>();
    private StudentAnalysisTraceabilityResponse traceability;
    private List<StudentAnalysisGateResponse> gates = new ArrayList<>();
    private StudentAnalysisMaterialsResponse materials;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getAssessmentId() {
        return assessmentId;
    }

    public void setAssessmentId(String assessmentId) {
        this.assessmentId = assessmentId;
    }

    public String getSubmissionId() {
        return submissionId;
    }

    public void setSubmissionId(String submissionId) {
        this.submissionId = submissionId;
    }

    public String getFinalResultId() {
        return finalResultId;
    }

    public void setFinalResultId(String finalResultId) {
        this.finalResultId = finalResultId;
    }

    public String getStudentId() {
        return studentId;
    }

    public void setStudentId(String studentId) {
        this.studentId = studentId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getStudentNumber() {
        return studentNumber;
    }

    public void setStudentNumber(String studentNumber) {
        this.studentNumber = studentNumber;
    }

    public String getAnonymousId() {
        return anonymousId;
    }

    public void setAnonymousId(String anonymousId) {
        this.anonymousId = anonymousId;
    }

    public BigDecimal getScore() {
        return score;
    }

    public void setScore(BigDecimal score) {
        this.score = score;
    }

    public BigDecimal getPercentileScore() {
        return percentileScore;
    }

    public void setPercentileScore(BigDecimal percentileScore) {
        this.percentileScore = percentileScore;
    }

    public String getGrade() {
        return grade;
    }

    public void setGrade(String grade) {
        this.grade = grade;
    }

    public BigDecimal getConfidence() {
        return confidence;
    }

    public void setConfidence(BigDecimal confidence) {
        this.confidence = confidence;
    }

    public String getReviewStatus() {
        return reviewStatus;
    }

    public void setReviewStatus(String reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    public Object getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(Object confirmedAt) {
        this.confirmedAt = confirmedAt;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public List<String> getQualityFindings() {
        return qualityFindings;
    }

    public void setQualityFindings(List<String> qualityFindings) {
        this.qualityFindings = qualityFindings;
    }

    public List<StudentAnalysisDimensionResponse> getDimensions() {
        return dimensions;
    }

    public void setDimensions(List<StudentAnalysisDimensionResponse> dimensions) {
        this.dimensions = dimensions;
    }

    public StudentAnalysisTraceabilityResponse getTraceability() {
        return traceability;
    }

    public void setTraceability(StudentAnalysisTraceabilityResponse traceability) {
        this.traceability = traceability;
    }

    public List<StudentAnalysisGateResponse> getGates() {
        return gates;
    }

    public void setGates(List<StudentAnalysisGateResponse> gates) {
        this.gates = gates;
    }

    public StudentAnalysisMaterialsResponse getMaterials() {
        return materials;
    }

    public void setMaterials(StudentAnalysisMaterialsResponse materials) {
        this.materials = materials;
    }
}
