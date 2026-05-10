package com.homeworkgrader.dto;

import java.util.ArrayList;
import java.util.List;

public class StudentAnalysisTraceabilityResponse {
    private List<String> requirements = new ArrayList<>();
    private List<StudentAnalysisCoverageResponse> hldCoverage = new ArrayList<>();
    private List<StudentAnalysisCoverageResponse> lldCoverage = new ArrayList<>();
    private List<String> uncoveredRequirements = new ArrayList<>();

    public List<String> getRequirements() {
        return requirements;
    }

    public void setRequirements(List<String> requirements) {
        this.requirements = requirements;
    }

    public List<StudentAnalysisCoverageResponse> getHldCoverage() {
        return hldCoverage;
    }

    public void setHldCoverage(List<StudentAnalysisCoverageResponse> hldCoverage) {
        this.hldCoverage = hldCoverage;
    }

    public List<StudentAnalysisCoverageResponse> getLldCoverage() {
        return lldCoverage;
    }

    public void setLldCoverage(List<StudentAnalysisCoverageResponse> lldCoverage) {
        this.lldCoverage = lldCoverage;
    }

    public List<String> getUncoveredRequirements() {
        return uncoveredRequirements;
    }

    public void setUncoveredRequirements(List<String> uncoveredRequirements) {
        this.uncoveredRequirements = uncoveredRequirements;
    }
}
