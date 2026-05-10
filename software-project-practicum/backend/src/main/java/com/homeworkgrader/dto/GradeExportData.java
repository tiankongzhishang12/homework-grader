package com.homeworkgrader.dto;

import java.util.ArrayList;
import java.util.List;

public class GradeExportData {
    private Long assessmentId;
    private Long exportId;
    private GradeExportMeta meta;
    private List<GradeExportSummaryRow> summaryRows = new ArrayList<>();
    private List<GradeExportDetailRow> detailRows = new ArrayList<>();
    private List<GradeExportRiskRow> riskRows = new ArrayList<>();

    public Long getAssessmentId() { return assessmentId; }
    public void setAssessmentId(Long assessmentId) { this.assessmentId = assessmentId; }
    public Long getExportId() { return exportId; }
    public void setExportId(Long exportId) { this.exportId = exportId; }
    public GradeExportMeta getMeta() { return meta; }
    public void setMeta(GradeExportMeta meta) { this.meta = meta; }
    public List<GradeExportSummaryRow> getSummaryRows() { return summaryRows; }
    public void setSummaryRows(List<GradeExportSummaryRow> summaryRows) { this.summaryRows = summaryRows; }
    public List<GradeExportDetailRow> getDetailRows() { return detailRows; }
    public void setDetailRows(List<GradeExportDetailRow> detailRows) { this.detailRows = detailRows; }
    public List<GradeExportRiskRow> getRiskRows() { return riskRows; }
    public void setRiskRows(List<GradeExportRiskRow> riskRows) { this.riskRows = riskRows; }
}
