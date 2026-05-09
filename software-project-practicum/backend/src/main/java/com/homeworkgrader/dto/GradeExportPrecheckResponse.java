package com.homeworkgrader.dto;

import java.util.ArrayList;
import java.util.List;

public class GradeExportPrecheckResponse {
    private Long assessmentId;
    private boolean canExport;
    private String exportLevel;
    private Summary summary;
    private List<Issue> warnings = new ArrayList<>();
    private List<Issue> blockers = new ArrayList<>();
    private String suggestedAction;

    public Long getAssessmentId() {
        return assessmentId;
    }

    public void setAssessmentId(Long assessmentId) {
        this.assessmentId = assessmentId;
    }

    public boolean isCanExport() {
        return canExport;
    }

    public void setCanExport(boolean canExport) {
        this.canExport = canExport;
    }

    public String getExportLevel() {
        return exportLevel;
    }

    public void setExportLevel(String exportLevel) {
        this.exportLevel = exportLevel;
    }

    public Summary getSummary() {
        return summary;
    }

    public void setSummary(Summary summary) {
        this.summary = summary;
    }

    public List<Issue> getWarnings() {
        return warnings;
    }

    public void setWarnings(List<Issue> warnings) {
        this.warnings = warnings;
    }

    public List<Issue> getBlockers() {
        return blockers;
    }

    public void setBlockers(List<Issue> blockers) {
        this.blockers = blockers;
    }

    public String getSuggestedAction() {
        return suggestedAction;
    }

    public void setSuggestedAction(String suggestedAction) {
        this.suggestedAction = suggestedAction;
    }

    public static class Summary {
        private int totalStudents;
        private int submittedStudents;
        private int gradedStudents;
        private int confirmedStudents;
        private int reviewRequiredStudents;
        private int lowConfidenceStudents;
        private int failedStudents;
        private int missingResultStudents;

        public int getTotalStudents() {
            return totalStudents;
        }

        public void setTotalStudents(int totalStudents) {
            this.totalStudents = totalStudents;
        }

        public int getSubmittedStudents() {
            return submittedStudents;
        }

        public void setSubmittedStudents(int submittedStudents) {
            this.submittedStudents = submittedStudents;
        }

        public int getGradedStudents() {
            return gradedStudents;
        }

        public void setGradedStudents(int gradedStudents) {
            this.gradedStudents = gradedStudents;
        }

        public int getConfirmedStudents() {
            return confirmedStudents;
        }

        public void setConfirmedStudents(int confirmedStudents) {
            this.confirmedStudents = confirmedStudents;
        }

        public int getReviewRequiredStudents() {
            return reviewRequiredStudents;
        }

        public void setReviewRequiredStudents(int reviewRequiredStudents) {
            this.reviewRequiredStudents = reviewRequiredStudents;
        }

        public int getLowConfidenceStudents() {
            return lowConfidenceStudents;
        }

        public void setLowConfidenceStudents(int lowConfidenceStudents) {
            this.lowConfidenceStudents = lowConfidenceStudents;
        }

        public int getFailedStudents() {
            return failedStudents;
        }

        public void setFailedStudents(int failedStudents) {
            this.failedStudents = failedStudents;
        }

        public int getMissingResultStudents() {
            return missingResultStudents;
        }

        public void setMissingResultStudents(int missingResultStudents) {
            this.missingResultStudents = missingResultStudents;
        }
    }

    public static class Issue {
        private String type;
        private String level;
        private int studentCount;
        private String message;

        public Issue() {
        }

        public Issue(String type, String level, int studentCount, String message) {
            this.type = type;
            this.level = level;
            this.studentCount = studentCount;
            this.message = message;
        }

        public String getType() {
            return type;
        }

        public void setType(String type) {
            this.type = type;
        }

        public String getLevel() {
            return level;
        }

        public void setLevel(String level) {
            this.level = level;
        }

        public int getStudentCount() {
            return studentCount;
        }

        public void setStudentCount(int studentCount) {
            this.studentCount = studentCount;
        }

        public String getMessage() {
            return message;
        }

        public void setMessage(String message) {
            this.message = message;
        }
    }
}
