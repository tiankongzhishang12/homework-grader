package com.homeworkgrader.dto;

import java.math.BigDecimal;

public class RubricCompileRequest {
    private String teacherText;
    private String taskName;
    private BigDecimal totalScore;
    private String language;

    public String getTeacherText() {
        return teacherText;
    }

    public void setTeacherText(String teacherText) {
        this.teacherText = teacherText;
    }

    public String getTaskName() {
        return taskName;
    }

    public void setTaskName(String taskName) {
        this.taskName = taskName;
    }

    public BigDecimal getTotalScore() {
        return totalScore;
    }

    public void setTotalScore(BigDecimal totalScore) {
        this.totalScore = totalScore;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }
}
