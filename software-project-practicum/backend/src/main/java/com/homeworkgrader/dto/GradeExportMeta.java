package com.homeworkgrader.dto;

public class GradeExportMeta {
    private Long exportId;
    private Long assessmentId;
    private String assessmentTitle;
    private String courseName;
    private String courseCode;
    private String createdAt;
    private String exportLevel;
    private Integer totalStudents;
    private Integer submittedStudents;
    private Integer gradedStudents;
    private Integer reviewRequiredStudents;
    private Integer lowConfidenceStudents;
    private Integer warningCount;
    private Integer blockerCount;
    private String fileName;

    public Long getExportId() { return exportId; }
    public void setExportId(Long exportId) { this.exportId = exportId; }
    public Long getAssessmentId() { return assessmentId; }
    public void setAssessmentId(Long assessmentId) { this.assessmentId = assessmentId; }
    public String getAssessmentTitle() { return assessmentTitle; }
    public void setAssessmentTitle(String assessmentTitle) { this.assessmentTitle = assessmentTitle; }
    public String getCourseName() { return courseName; }
    public void setCourseName(String courseName) { this.courseName = courseName; }
    public String getCourseCode() { return courseCode; }
    public void setCourseCode(String courseCode) { this.courseCode = courseCode; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getExportLevel() { return exportLevel; }
    public void setExportLevel(String exportLevel) { this.exportLevel = exportLevel; }
    public Integer getTotalStudents() { return totalStudents; }
    public void setTotalStudents(Integer totalStudents) { this.totalStudents = totalStudents; }
    public Integer getSubmittedStudents() { return submittedStudents; }
    public void setSubmittedStudents(Integer submittedStudents) { this.submittedStudents = submittedStudents; }
    public Integer getGradedStudents() { return gradedStudents; }
    public void setGradedStudents(Integer gradedStudents) { this.gradedStudents = gradedStudents; }
    public Integer getReviewRequiredStudents() { return reviewRequiredStudents; }
    public void setReviewRequiredStudents(Integer reviewRequiredStudents) { this.reviewRequiredStudents = reviewRequiredStudents; }
    public Integer getLowConfidenceStudents() { return lowConfidenceStudents; }
    public void setLowConfidenceStudents(Integer lowConfidenceStudents) { this.lowConfidenceStudents = lowConfidenceStudents; }
    public Integer getWarningCount() { return warningCount; }
    public void setWarningCount(Integer warningCount) { this.warningCount = warningCount; }
    public Integer getBlockerCount() { return blockerCount; }
    public void setBlockerCount(Integer blockerCount) { this.blockerCount = blockerCount; }
    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }
}
