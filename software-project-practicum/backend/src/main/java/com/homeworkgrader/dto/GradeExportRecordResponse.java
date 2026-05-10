package com.homeworkgrader.dto;

public class GradeExportRecordResponse {
    private Long id;
    private Long assessmentId;
    private String fileName;
    private String filePath;
    private Long fileSize;
    private String status;
    private String exportLevel;
    private Boolean canExport;
    private Integer totalStudents;
    private Integer submittedStudents;
    private Integer gradedStudents;
    private Integer confirmedStudents;
    private Integer reviewRequiredStudents;
    private Integer lowConfidenceStudents;
    private Integer failedStudents;
    private Integer missingResultStudents;
    private Integer warningCount;
    private Integer blockerCount;
    private String createdAt;
    private String startedAt;
    private String completedAt;
    private String failedReason;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getAssessmentId() { return assessmentId; }
    public void setAssessmentId(Long assessmentId) { this.assessmentId = assessmentId; }
    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }
    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }
    public Long getFileSize() { return fileSize; }
    public void setFileSize(Long fileSize) { this.fileSize = fileSize; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getExportLevel() { return exportLevel; }
    public void setExportLevel(String exportLevel) { this.exportLevel = exportLevel; }
    public Boolean getCanExport() { return canExport; }
    public void setCanExport(Boolean canExport) { this.canExport = canExport; }
    public Integer getTotalStudents() { return totalStudents; }
    public void setTotalStudents(Integer totalStudents) { this.totalStudents = totalStudents; }
    public Integer getSubmittedStudents() { return submittedStudents; }
    public void setSubmittedStudents(Integer submittedStudents) { this.submittedStudents = submittedStudents; }
    public Integer getGradedStudents() { return gradedStudents; }
    public void setGradedStudents(Integer gradedStudents) { this.gradedStudents = gradedStudents; }
    public Integer getConfirmedStudents() { return confirmedStudents; }
    public void setConfirmedStudents(Integer confirmedStudents) { this.confirmedStudents = confirmedStudents; }
    public Integer getReviewRequiredStudents() { return reviewRequiredStudents; }
    public void setReviewRequiredStudents(Integer reviewRequiredStudents) { this.reviewRequiredStudents = reviewRequiredStudents; }
    public Integer getLowConfidenceStudents() { return lowConfidenceStudents; }
    public void setLowConfidenceStudents(Integer lowConfidenceStudents) { this.lowConfidenceStudents = lowConfidenceStudents; }
    public Integer getFailedStudents() { return failedStudents; }
    public void setFailedStudents(Integer failedStudents) { this.failedStudents = failedStudents; }
    public Integer getMissingResultStudents() { return missingResultStudents; }
    public void setMissingResultStudents(Integer missingResultStudents) { this.missingResultStudents = missingResultStudents; }
    public Integer getWarningCount() { return warningCount; }
    public void setWarningCount(Integer warningCount) { this.warningCount = warningCount; }
    public Integer getBlockerCount() { return blockerCount; }
    public void setBlockerCount(Integer blockerCount) { this.blockerCount = blockerCount; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getStartedAt() { return startedAt; }
    public void setStartedAt(String startedAt) { this.startedAt = startedAt; }
    public String getCompletedAt() { return completedAt; }
    public void setCompletedAt(String completedAt) { this.completedAt = completedAt; }
    public String getFailedReason() { return failedReason; }
    public void setFailedReason(String failedReason) { this.failedReason = failedReason; }
}
