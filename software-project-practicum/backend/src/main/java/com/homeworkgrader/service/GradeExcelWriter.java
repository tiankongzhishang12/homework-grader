package com.homeworkgrader.service;

import com.homeworkgrader.dto.GradeExportData;
import com.homeworkgrader.dto.GradeExportDetailRow;
import com.homeworkgrader.dto.GradeExportMeta;
import com.homeworkgrader.dto.GradeExportRiskRow;
import com.homeworkgrader.dto.GradeExportSummaryRow;
import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellStyle;
import org.apache.poi.ss.usermodel.Font;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class GradeExcelWriter {
    private static final Logger log = LoggerFactory.getLogger(GradeExcelWriter.class);

    public void writeToFile(GradeExportData data, Path targetPath) throws IOException {
        try (Workbook workbook = new XSSFWorkbook()) {
            CellStyle headerStyle = workbook.createCellStyle();
            Font headerFont = workbook.createFont();
            headerFont.setBold(true);
            headerStyle.setFont(headerFont);

            writeSummarySheet(workbook, headerStyle, data);
            writeDetailSheet(workbook, headerStyle, data);
            writeRiskSheet(workbook, headerStyle, data);
            writeMetaSheet(workbook, headerStyle, data);

            if (targetPath.getParent() != null) {
                Files.createDirectories(targetPath.getParent());
            }
            try (OutputStream output = Files.newOutputStream(targetPath)) {
                workbook.write(output);
            }
        } catch (IOException ex) {
            log.error("Failed to write grade export Excel file: targetPath={}", targetPath, ex);
            throw ex;
        }
    }

    private void writeSummarySheet(Workbook workbook, CellStyle headerStyle, GradeExportData data) {
        Sheet sheet = workbook.createSheet("成绩总表");
        writeHeader(sheet, headerStyle, "学号", "姓名", "提交ID", "最终成绩ID", "总分", "成绩来源", "复核状态", "整体置信度", "确认时间", "模型名称");
        int rowIndex = 1;
        for (GradeExportSummaryRow item : data.getSummaryRows()) {
            Row row = sheet.createRow(rowIndex++);
            write(row, 0, item.getStudentNo());
            write(row, 1, item.getStudentName());
            write(row, 2, item.getSubmissionId());
            write(row, 3, item.getFinalResultId());
            write(row, 4, item.getFinalScore());
            write(row, 5, item.getScoreSource());
            write(row, 6, item.getReviewStatus());
            write(row, 7, item.getConfidence());
            write(row, 8, item.getConfirmedAt());
            write(row, 9, item.getModelName());
        }
        autosize(sheet, 10);
    }

    private void writeDetailSheet(Workbook workbook, CellStyle headerStyle, GradeExportData data) {
        Sheet sheet = workbook.createSheet("评分项明细");
        writeHeader(sheet, headerStyle, "学号", "姓名", "题号", "题型区块", "评分项", "得分", "满分", "置信度", "是否需要复核", "评分证据", "评语");
        int rowIndex = 1;
        for (GradeExportDetailRow item : data.getDetailRows()) {
            Row row = sheet.createRow(rowIndex++);
            write(row, 0, item.getStudentNo());
            write(row, 1, item.getStudentName());
            write(row, 2, item.getQuestionNo());
            write(row, 3, item.getSectionName());
            write(row, 4, item.getRubricName());
            write(row, 5, item.getScore());
            write(row, 6, item.getMaxScore());
            write(row, 7, item.getConfidence());
            write(row, 8, Boolean.TRUE.equals(item.getNeedsReview()) ? "是" : "否");
            write(row, 9, item.getEvidenceText());
            write(row, 10, item.getCommentText());
        }
        autosize(sheet, 11);
    }

    private void writeRiskSheet(Workbook workbook, CellStyle headerStyle, GradeExportData data) {
        Sheet sheet = workbook.createSheet("风险样本");
        writeHeader(sheet, headerStyle, "学号", "姓名", "风险类型", "风险原因", "当前复核状态", "建议操作");
        int rowIndex = 1;
        for (GradeExportRiskRow item : data.getRiskRows()) {
            Row row = sheet.createRow(rowIndex++);
            write(row, 0, item.getStudentNo());
            write(row, 1, item.getStudentName());
            write(row, 2, item.getRiskType());
            write(row, 3, item.getRiskReason());
            write(row, 4, item.getReviewStatus());
            write(row, 5, item.getSuggestedAction());
        }
        autosize(sheet, 6);
    }

    private void writeMetaSheet(Workbook workbook, CellStyle headerStyle, GradeExportData data) {
        Sheet sheet = workbook.createSheet("导出元信息");
        writeHeader(sheet, headerStyle, "字段", "值");
        GradeExportMeta meta = data.getMeta();
        int rowIndex = 1;
        rowIndex = writeMeta(sheet, rowIndex, "导出记录ID", meta.getExportId());
        rowIndex = writeMeta(sheet, rowIndex, "考核ID", meta.getAssessmentId());
        rowIndex = writeMeta(sheet, rowIndex, "任务名称", meta.getAssessmentTitle());
        rowIndex = writeMeta(sheet, rowIndex, "课程名称", meta.getCourseName());
        rowIndex = writeMeta(sheet, rowIndex, "课程代码", meta.getCourseCode());
        rowIndex = writeMeta(sheet, rowIndex, "导出时间", meta.getCreatedAt());
        rowIndex = writeMeta(sheet, rowIndex, "导出前检查等级", meta.getExportLevel());
        rowIndex = writeMeta(sheet, rowIndex, "总人数", meta.getTotalStudents());
        rowIndex = writeMeta(sheet, rowIndex, "已提交人数", meta.getSubmittedStudents());
        rowIndex = writeMeta(sheet, rowIndex, "已评分人数", meta.getGradedStudents());
        rowIndex = writeMeta(sheet, rowIndex, "待确认人数", meta.getReviewRequiredStudents());
        rowIndex = writeMeta(sheet, rowIndex, "低置信度人数", meta.getLowConfidenceStudents());
        rowIndex = writeMeta(sheet, rowIndex, "风险数量", meta.getWarningCount());
        rowIndex = writeMeta(sheet, rowIndex, "阻断数量", meta.getBlockerCount());
        writeMeta(sheet, rowIndex, "文件名", meta.getFileName());
        autosize(sheet, 2);
    }

    private void writeHeader(Sheet sheet, CellStyle headerStyle, String... headers) {
        Row row = sheet.createRow(0);
        for (int i = 0; i < headers.length; i++) {
            Cell cell = row.createCell(i);
            cell.setCellValue(headers[i]);
            cell.setCellStyle(headerStyle);
        }
    }

    private int writeMeta(Sheet sheet, int rowIndex, String field, Object value) {
        Row row = sheet.createRow(rowIndex);
        write(row, 0, field);
        write(row, 1, value);
        return rowIndex + 1;
    }

    private void write(Row row, int index, Object value) {
        Cell cell = row.createCell(index);
        if (value == null) {
            cell.setCellValue("");
        } else if (value instanceof BigDecimal) {
            cell.setCellValue(((BigDecimal) value).doubleValue());
        } else if (value instanceof Number) {
            cell.setCellValue(((Number) value).doubleValue());
        } else {
            cell.setCellValue(String.valueOf(value));
        }
    }

    private void autosize(Sheet sheet, int columns) {
        for (int i = 0; i < columns; i++) {
            sheet.autoSizeColumn(i);
            int width = sheet.getColumnWidth(i);
            sheet.setColumnWidth(i, Math.min(Math.max(width + 512, 3000), 16000));
        }
    }
}
