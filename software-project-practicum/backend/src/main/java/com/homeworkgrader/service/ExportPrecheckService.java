package com.homeworkgrader.service;

import com.homeworkgrader.dto.GradeExportPrecheckResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.FileNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class ExportPrecheckService {
    private final CrudJdbcRepository repository;

    public ExportPrecheckService(CrudJdbcRepository repository) {
        this.repository = repository;
    }

    public GradeExportPrecheckResponse precheck(Long assessmentId) throws FileNotFoundException {
        Integer exists = repository.queryForInteger(
                "select count(*) from assessment where id = :assessmentId",
                Maps.of("assessmentId", assessmentId)
        );
        if (exists == null || exists == 0) {
            throw new FileNotFoundException("未找到当前考核任务，无法执行导出前检查。");
        }

        GradeExportPrecheckResponse.Summary summary = new GradeExportPrecheckResponse.Summary();
        summary.setTotalStudents(countTotalStudents(assessmentId));
        summary.setSubmittedStudents(countSubmittedStudents(assessmentId));
        summary.setGradedStudents(countGradedStudents(assessmentId));
        summary.setConfirmedStudents(countByReviewStatus(assessmentId, "'CONFIRMED', 'PUBLISHED'"));
        summary.setReviewRequiredStudents(countByReviewStatus(assessmentId, "'AI_GENERATED', 'REVIEW_REQUIRED'"));
        summary.setLowConfidenceStudents(countLowConfidenceStudents(assessmentId));
        // submission table has no grading_status column in the current schema; keep this at 0 until grading failure state is persisted per submission.
        summary.setFailedStudents(0);
        summary.setMissingResultStudents(Math.max(0, summary.getSubmittedStudents() - summary.getGradedStudents()));

        GradeExportPrecheckResponse response = new GradeExportPrecheckResponse();
        response.setAssessmentId(assessmentId);
        response.setSummary(summary);

        if (summary.getSubmittedStudents() == 0) {
            response.getBlockers().add(new GradeExportPrecheckResponse.Issue(
                    "NO_SUBMISSION", "BLOCK", 0, "当前任务还没有学生提交，暂不可导出。"
            ));
        }
        if (summary.getGradedStudents() == 0) {
            response.getBlockers().add(new GradeExportPrecheckResponse.Issue(
                    "NO_GRADED_RESULT", "BLOCK", 0, "当前任务还没有评分结果，暂不可导出。"
            ));
        }
        if (summary.getReviewRequiredStudents() > 0) {
            response.getWarnings().add(new GradeExportPrecheckResponse.Issue(
                    "REVIEW_REQUIRED", "WARN", summary.getReviewRequiredStudents(),
                    "当前有 " + summary.getReviewRequiredStudents() + " 名学生尚未完成教师确认。"
            ));
        }
        if (summary.getLowConfidenceStudents() > 0) {
            response.getWarnings().add(new GradeExportPrecheckResponse.Issue(
                    "LOW_CONFIDENCE", "WARN", summary.getLowConfidenceStudents(),
                    "当前有 " + summary.getLowConfidenceStudents() + " 名学生存在低置信度评分。"
            ));
        }
        if (summary.getFailedStudents() > 0) {
            response.getWarnings().add(new GradeExportPrecheckResponse.Issue(
                    "GRADING_FAILED", "WARN", summary.getFailedStudents(),
                    "当前有 " + summary.getFailedStudents() + " 名学生评分失败，建议处理后再导出。"
            ));
        }
        if (summary.getMissingResultStudents() > 0 && summary.getGradedStudents() > 0) {
            response.getWarnings().add(new GradeExportPrecheckResponse.Issue(
                    "MISSING_RESULT", "WARN", summary.getMissingResultStudents(),
                    "当前有 " + summary.getMissingResultStudents() + " 名已提交学生缺少最终成绩。"
            ));
        }

        if (!response.getBlockers().isEmpty()) {
            response.setCanExport(false);
            response.setExportLevel("BLOCK");
            response.setSuggestedAction("请先处理阻断问题，再执行成绩导出。");
        } else if (!response.getWarnings().isEmpty()) {
            response.setCanExport(true);
            response.setExportLevel("WARN");
            response.setSuggestedAction("建议先完成复核，也可以继续导出并记录风险确认。");
        } else {
            response.setCanExport(true);
            response.setExportLevel("PASS");
            response.setSuggestedAction("当前成绩结果满足导出条件，可以直接导出。");
        }
        return response;
    }

    private int countTotalStudents(Long assessmentId) {
        Integer value = repository.queryForInteger(
                "select count(distinct tcs.student_id) from assessment a " +
                        "join course_offering co on co.id = a.course_offering_id " +
                        "join teaching_class tc on tc.course_offering_id = co.id " +
                        "join teaching_class_student tcs on tcs.teaching_class_id = tc.id " +
                        "where a.id = :assessmentId",
                Maps.of("assessmentId", assessmentId)
        );
        return value == null ? 0 : value;
    }

    private int countSubmittedStudents(Long assessmentId) {
        Integer value = repository.queryForInteger(
                "select count(distinct student_id) from submission where assessment_id = :assessmentId and status = 1",
                Maps.of("assessmentId", assessmentId)
        );
        return value == null ? 0 : value;
    }

    private int countGradedStudents(Long assessmentId) {
        Integer value = repository.queryForInteger(
                "select count(distinct s.student_id) from submission s join final_result fr on fr.submission_id = s.id " +
                        "where s.assessment_id = :assessmentId and s.status = 1",
                Maps.of("assessmentId", assessmentId)
        );
        return value == null ? 0 : value;
    }

    private int countByReviewStatus(Long assessmentId, String statuses) {
        Integer value = repository.queryForInteger(
                "select count(distinct s.student_id) from submission s join final_result fr on fr.submission_id = s.id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 and fr.review_status in (" + statuses + ")",
                Maps.of("assessmentId", assessmentId)
        );
        return value == null ? 0 : value;
    }

    private int countLowConfidenceStudents(Long assessmentId) {
        Integer value = repository.queryForInteger(
                "select count(distinct s.student_id) from submission s " +
                        "join final_result fr on fr.submission_id = s.id " +
                        "join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and gr.confidence is not null and gr.confidence > 0 and gr.confidence < 0.8",
                Maps.of("assessmentId", assessmentId)
        );
        return value == null ? 0 : value;
    }
}
