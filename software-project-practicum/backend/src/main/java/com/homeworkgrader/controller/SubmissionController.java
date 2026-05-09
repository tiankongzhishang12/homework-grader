package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.SubmissionService;
import com.homeworkgrader.storage.FileStorageService;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
public class SubmissionController {
    private final CrudJdbcRepository repository;
    private final SubmissionService submissionService;
    private final FileStorageService storageService;

    public SubmissionController(CrudJdbcRepository repository, SubmissionService submissionService, FileStorageService storageService) {
        this.repository = repository;
        this.submissionService = submissionService;
        this.storageService = storageService;
    }

    @PostMapping("/assessments/{id}/submissions/upload")
    public ApiResponse<?> upload(@PathVariable Long id, @RequestParam Long studentId, @RequestParam MultipartFile file) throws IOException {
        return ApiResponse.ok(submissionService.upload(id, studentId, file));
    }

    @GetMapping("/assessments/{id}/submissions")
    public ApiResponse<?> submissions(@PathVariable Long id) {
        return ApiResponse.ok(repository.query(
                "select s.id, s.assessment_id, s.student_id, st.student_no, st.student_name, " +
                        "s.source_submission_id, s.submit_status, s.submitted_at, s.attempt_no, " +
                        "sa.file_name, sa.file_ext, fr.id final_result_id, fr.final_score, fr.review_status, " +
                        "case when gr.status = 'FAILED' then 'FAILED' when fr.id is not null and fr.selected_grading_run_id is not null then 'GRADED' else 'PENDING' end grading_status, " +
                        "case when fr.id is not null then true else false end has_final_result " +
                        "from submission s " +
                        "left join student st on st.id = s.student_id " +
                        "left join submission_asset sa on sa.submission_id = s.id and sa.asset_type = 'ORIGINAL' " +
                        "left join final_result fr on fr.submission_id = s.id " +
                        "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId order by s.submitted_at desc, s.id desc",
                com.homeworkgrader.util.Maps.of("assessmentId", id)
        ));
    }

    @GetMapping("/assessments/{id}/submissions/summary")
    public ApiResponse<?> submissionSummary(@PathVariable Long id) {
        Integer studentCount = repository.queryForInteger(
                "select count(distinct tcs.student_id) from assessment a " +
                        "join course_offering co on co.id = a.course_offering_id " +
                        "join teaching_class tc on tc.course_offering_id = co.id " +
                        "join teaching_class_student tcs on tcs.teaching_class_id = tc.id " +
                        "where a.id = :assessmentId",
                com.homeworkgrader.util.Maps.of("assessmentId", id)
        );
        Integer submittedCount = repository.queryForInteger("select count(*) from submission where assessment_id = :assessmentId", com.homeworkgrader.util.Maps.of("assessmentId", id));
        Integer validSubmissionCount = repository.queryForInteger("select count(*) from submission where assessment_id = :assessmentId and status = 1 and submit_status = 'UPLOADED'", com.homeworkgrader.util.Maps.of("assessmentId", id));
        Integer pendingGradingCount = repository.queryForInteger(
                "select count(*) from submission s left join final_result fr on fr.submission_id = s.id " +
                        "where s.assessment_id = :assessmentId and s.status = 1 " +
                        "and s.attempt_no = (select max(s2.attempt_no) from submission s2 where s2.assessment_id = s.assessment_id and s2.student_id = s.student_id and s2.status = 1) " +
                        "and (fr.id is null or fr.selected_grading_run_id is null)",
                com.homeworkgrader.util.Maps.of("assessmentId", id)
        );
        Integer gradedCount = repository.queryForInteger(
                "select count(*) from submission s join final_result fr on fr.submission_id = s.id where s.assessment_id = :assessmentId and fr.selected_grading_run_id is not null",
                com.homeworkgrader.util.Maps.of("assessmentId", id)
        );
        Integer failedCount = repository.queryForInteger(
                "select count(*) from submission s left join final_result fr on fr.submission_id = s.id left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "where s.assessment_id = :assessmentId and (s.submit_status not in ('UPLOADED', 'SUBMITTED') or gr.status = 'FAILED')",
                com.homeworkgrader.util.Maps.of("assessmentId", id)
        );
        Map<String, Object> summary = new java.util.HashMap<>();
        summary.put("assessmentId", id);
        summary.put("studentCount", studentCount == null ? 0 : studentCount);
        summary.put("submittedCount", submittedCount == null ? 0 : submittedCount);
        summary.put("validSubmissionCount", validSubmissionCount == null ? 0 : validSubmissionCount);
        summary.put("pendingGradingCount", pendingGradingCount == null ? 0 : pendingGradingCount);
        summary.put("gradedCount", gradedCount == null ? 0 : gradedCount);
        summary.put("failedCount", failedCount == null ? 0 : failedCount);
        summary.put("supportedExtensions", java.util.Arrays.asList("doc", "docx", "pdf"));
        return ApiResponse.ok(summary);
    }

    @GetMapping("/submissions/{id}")
    public ApiResponse<?> submission(@PathVariable Long id) {
        return ApiResponse.ok(repository.get("submission", id));
    }

    @GetMapping("/submissions/{id}/assets/{assetId}/download")
    public ResponseEntity<Resource> download(@PathVariable Long id, @PathVariable Long assetId) throws IOException {
        Map<String, Object> asset = repository.get("submission_asset", assetId);
        if (!id.equals(((Number) asset.get("submission_id")).longValue())) {
            throw new FileNotFoundException("资源不属于该提交");
        }
        Path path = storageService.resolve((String) asset.get("file_path"));
        return ResponseEntity.ok(new FileSystemResource(path));
    }
}
