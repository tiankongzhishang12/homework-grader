package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import java.io.FileNotFoundException;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@CrossOrigin(
        originPatterns = {"http://localhost:*", "http://127.0.0.1:*"},
        allowCredentials = "true"
)
public class FrontendViewController {
    private static final String DEMO_TASK_ID = "answer-card-demo";
    private static final String DEMO_ASSESSMENT_TITLE = "答题卡评分联调测试";

    private final NamedParameterJdbcTemplate jdbc;
    private volatile boolean batchStarted = false;

    public FrontendViewController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/tasks")
    public ApiResponse<?> tasks() {
        List<Map<String, Object>> rows = queryTaskRows();
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            tasks.add(toTaskDetail(row));
        }
        return ApiResponse.ok(tasks);
    }

    @GetMapping("/tasks/{taskId}")
    public ApiResponse<?> task(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        Map<String, Object> row = singleTaskRow();
        if (row == null) {
            throw new FileNotFoundException("未找到答题卡演示任务，请先执行 database/answer_card_demo_seed.sql");
        }
        return ApiResponse.ok(toTaskDetail(row));
    }

    @GetMapping("/tasks/{taskId}/config-status")
    public ApiResponse<?> configStatus(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(map("blockers", new ArrayList<>()));
    }

    @GetMapping("/tasks/{taskId}/answers")
    public ApiResponse<?> answers(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(Arrays.asList(map(
                "id", "answer-card-standard-v1",
                "version", "v1.0",
                "fileName", "软件需求答题卡标准答案.yaml",
                "uploadedAt", "2026-04-18 09:00",
                "parseStatus", "in_use",
                "itemCount", 33,
                "activatedAt", "2026-04-18 09:20",
                "status", "in_use",
                "current", true
        )));
    }

    @PostMapping("/tasks/{taskId}/answers/{versionId}/activate")
    public ApiResponse<?> activateAnswer(@PathVariable String taskId, @PathVariable String versionId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(map("success", true));
    }

    @GetMapping("/rubrics")
    public ApiResponse<?> rubrics() {
        return ApiResponse.ok(Arrays.asList(demoRubric()));
    }

    @GetMapping("/tasks/{taskId}/rubric-binding")
    public ApiResponse<?> rubricBinding(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(demoRubric());
    }

    @GetMapping("/export-templates")
    public ApiResponse<?> exportTemplates() {
        return ApiResponse.ok(Arrays.asList(demoExportTemplate()));
    }

    @GetMapping("/tasks/{taskId}/export-template")
    public ApiResponse<?> currentExportTemplate(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(demoExportTemplate());
    }

    @GetMapping("/tasks/{taskId}/workspace")
    public ApiResponse<?> workspace(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(demoWorkspace("valid", "数据库种子数据已就绪，可用于前后端联调。"));
    }

    @PostMapping("/tasks/{taskId}/workspace/check")
    public ApiResponse<?> checkWorkspace(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(demoWorkspace("valid", "数据库、后端视图接口和演示任务配置检查通过。"));
    }

    @PostMapping("/tasks/{taskId}/workspace/init")
    public ApiResponse<?> initWorkspace(@PathVariable String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(demoWorkspace("valid", "演示工作区已初始化。"));
    }

    @PostMapping("/batch/start")
    public ApiResponse<?> startBatch(@RequestBody Map<String, Object> request) throws FileNotFoundException {
        ensureDemoTask(String.valueOf(request.get("taskId")));
        batchStarted = true;
        return ApiResponse.ok(map("success", true));
    }

    @GetMapping("/batch/progress")
    public ApiResponse<?> batchProgress(@RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        int total = studentRows().size();
        return ApiResponse.ok(map(
                "taskId", DEMO_TASK_ID,
                "status", "completed",
                "startedAt", batchStarted ? "2026-04-18 10:10:00" : null,
                "updatedAt", "2026-04-18 10:12:00",
                "total", total,
                "completed", total,
                "currentStepLabel", "已完成答题卡评分结果导入",
                "qualityFlags", Arrays.asList(
                        map("flag", "gate_warning", "count", total, "label", "需人工复核"),
                        map("flag", "low_confidence", "count", 1, "label", "低置信度样本")
                )
        ));
    }

    @GetMapping("/batch/logs")
    public ApiResponse<?> batchLogs(@RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(Arrays.asList(
                map("time", "2026-04-18 10:10:00", "level", "info", "message", "读取数据库中的 3 条答题卡种子数据。"),
                map("time", "2026-04-18 10:11:00", "level", "info", "message", "已聚合学生成绩、分区得分和复核标记。"),
                map("time", "2026-04-18 10:12:00", "level", "warn", "message", "3 个样本均带有系统复核建议。")
        ));
    }

    @GetMapping(value = "/students", params = "taskId")
    public ApiResponse<?> students(@RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(studentRows());
    }

    @GetMapping("/students/{studentId}")
    public ApiResponse<?> student(@PathVariable String studentId, @RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        Map<String, Object> row = singleStudentRow(studentId);
        if (row == null) {
            throw new FileNotFoundException("未找到学生评分结果：" + studentId);
        }
        return ApiResponse.ok(studentDetail(row));
    }

    @GetMapping("/analytics")
    public ApiResponse<?> analytics(@RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        List<Map<String, Object>> students = studentRows();
        double total = 0;
        int lowConfidence = 0;
        int review = 0;
        int[] bands = new int[] {0, 0, 0, 0, 0};
        for (Map<String, Object> student : students) {
            double score = toDouble(student.get("score"));
            total += score;
            if (toDouble(student.get("confidence")) < 0.8) lowConfidence++;
            if (!"通过".equals(student.get("gateStatus"))) review++;
            if (score >= 90) bands[0]++;
            else if (score >= 80) bands[1]++;
            else if (score >= 70) bands[2]++;
            else if (score >= 60) bands[3]++;
            else bands[4]++;
        }
        return ApiResponse.ok(map(
                "averageScore", students.isEmpty() ? 0 : Math.round(total / students.size() * 10.0) / 10.0,
                "totalStudents", students.size(),
                "lowConfidenceCount", lowConfidence,
                "gateWarningCount", review,
                "placeholderResidueCount", 0,
                "scoreBands", Arrays.asList(
                        map("label", "90-100", "value", bands[0]),
                        map("label", "80-89", "value", bands[1]),
                        map("label", "70-79", "value", bands[2]),
                        map("label", "60-69", "value", bands[3]),
                        map("label", "60以下", "value", bands[4])
                ),
                "topIssues", Arrays.asList(
                        map("title", "系统建议人工复核", "count", review, "detail", "答题卡图形题、填空字迹或主观题证据存在复核建议。"),
                        map("title", "综合建模题失分", "count", 2, "detail", "部分学生在用例图、E-R 图或 DFD 表达上存在结构缺失。"),
                        map("title", "低置信度区块", "count", lowConfidence, "detail", "张翼综合题置信度较低，建议优先查看。")
                )
        ));
    }

    @PostMapping("/batch/export")
    public ApiResponse<?> export(@RequestBody Map<String, Object> request) throws FileNotFoundException {
        ensureDemoTask(String.valueOf(request.get("taskId")));
        return ApiResponse.ok(exportRecord());
    }

    @GetMapping("/exports")
    public ApiResponse<?> exports(@RequestParam String taskId) throws FileNotFoundException {
        ensureDemoTask(taskId);
        return ApiResponse.ok(Arrays.asList(exportRecord()));
    }

    private List<Map<String, Object>> queryTaskRows() {
        return jdbc.queryForList(
                "select a.id assessment_id, a.title task_name, a.assessment_type, a.total_score, a.due_at, " +
                        "co.course_code, co.course_name, cofr.academic_year, cofr.term, tc.class_name, " +
                        "count(distinct s.id) submitted_count, count(distinct tcs.student_id) student_count, " +
                        "count(distinct fr.id) result_count " +
                        "from assessment a " +
                        "join course_offering cofr on cofr.id = a.course_offering_id " +
                        "join course co on co.id = cofr.course_id " +
                        "left join teaching_class tc on tc.course_offering_id = cofr.id " +
                        "left join teaching_class_student tcs on tcs.teaching_class_id = tc.id " +
                        "left join submission s on s.assessment_id = a.id " +
                        "left join final_result fr on fr.submission_id = s.id " +
                        "where a.title = :title " +
                        "group by a.id, a.title, a.assessment_type, a.total_score, a.due_at, co.course_code, co.course_name, cofr.academic_year, cofr.term, tc.class_name",
                params("title", DEMO_ASSESSMENT_TITLE)
        );
    }

    private Map<String, Object> singleTaskRow() {
        List<Map<String, Object>> rows = queryTaskRows();
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Map<String, Object> toTaskDetail(Map<String, Object> row) {
        int studentCount = toInt(row.get("student_count"));
        int submittedCount = toInt(row.get("submitted_count"));
        int resultCount = toInt(row.get("result_count"));
        String batchStatus = resultCount >= submittedCount && submittedCount > 0 ? "completed" : "idle";
        return map(
                "id", DEMO_TASK_ID,
                "courseName", row.get("course_name"),
                "className", row.get("class_name"),
                "taskName", row.get("task_name"),
                "taskType", "答题卡考试",
                "studentCount", studentCount,
                "submittedCount", submittedCount,
                "configReady", true,
                "configProgress", 100,
                "batchStatus", batchStatus,
                "nextAction", "查看 3 条答题卡种子数据的评分结果",
                "courseCode", row.get("course_code"),
                "term", row.get("academic_year") + "-" + row.get("term"),
                "score", toDouble(row.get("total_score")),
                "deadline", formatDate(row.get("due_at")),
                "description", "用于验证数据库、Spring Boot 后端和 Vue 前端完整链路的答题卡评分演示任务。",
                "configStatuses", map(
                        "answers", "in_use",
                        "rubric", "in_use",
                        "exportTemplate", "in_use",
                        "workspace", "valid"
                )
        );
    }

    private List<Map<String, Object>> studentRows() {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select st.student_no, st.student_name, s.source_submission_id, fr.final_score, fr.review_status, " +
                        "gr.confidence, " +
                        "sum(case when sir.needs_review = 1 then 1 else 0 end) review_item_count, " +
                        "sum(case when sir.confidence is not null and sir.confidence < 0.8 then 1 else 0 end) low_confidence_count " +
                        "from assessment a " +
                        "join submission s on s.assessment_id = a.id " +
                        "join student st on st.id = s.student_id " +
                        "join final_result fr on fr.submission_id = s.id " +
                        "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "left join score_item_result sir on sir.grading_run_id = gr.id " +
                        "where a.title = :title " +
                        "group by st.student_no, st.student_name, s.source_submission_id, fr.final_score, fr.review_status, gr.confidence " +
                        "order by st.student_no",
                params("title", DEMO_ASSESSMENT_TITLE)
        );
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(toStudentRow(row));
        }
        return result;
    }

    private Map<String, Object> singleStudentRow(String studentId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select st.id student_db_id, st.student_no, st.student_name, s.id submission_id, s.source_submission_id, " +
                        "fr.final_score, fr.review_status, gr.id grading_run_id, gr.confidence, er.summary_text, " +
                        "sum(case when sir.needs_review = 1 then 1 else 0 end) review_item_count, " +
                        "sum(case when sir.confidence is not null and sir.confidence < 0.8 then 1 else 0 end) low_confidence_count " +
                        "from assessment a " +
                        "join submission s on s.assessment_id = a.id " +
                        "join student st on st.id = s.student_id " +
                        "join final_result fr on fr.submission_id = s.id " +
                        "left join grading_run gr on gr.id = fr.selected_grading_run_id " +
                        "left join extraction_run xr on xr.id = gr.extraction_run_id " +
                        "left join extraction_result er on er.extraction_run_id = xr.id " +
                        "left join score_item_result sir on sir.grading_run_id = gr.id " +
                        "where a.title = :title and (st.student_no = :studentId or s.source_submission_id = :studentId) " +
                        "group by st.id, st.student_no, st.student_name, s.id, s.source_submission_id, fr.final_score, fr.review_status, gr.id, gr.confidence, er.summary_text",
                params("title", DEMO_ASSESSMENT_TITLE, "studentId", studentId)
        );
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Map<String, Object> toStudentRow(Map<String, Object> row) {
        double score = toDouble(row.get("final_score"));
        double confidence = toDouble(row.get("confidence"));
        int reviewCount = toInt(row.get("review_item_count"));
        int lowConfidenceCount = toInt(row.get("low_confidence_count"));
        List<String> riskTags = new ArrayList<>();
        if (reviewCount > 0) riskTags.add("需人工复核");
        if (lowConfidenceCount > 0 || confidence < 0.8) riskTags.add("低置信度");
        if (score < 70) riskTags.add("综合题失分");
        if (riskTags.isEmpty()) riskTags.add("可直接查看");
        return map(
                "id", row.get("student_no"),
                "studentNumber", row.get("student_no"),
                "name", row.get("student_name"),
                "anonymousId", row.get("source_submission_id"),
                "score", score,
                "grade", grade(score),
                "confidence", confidence,
                "gateStatus", "REVIEW_REQUIRED".equals(row.get("review_status")) ? "需复核" : "通过",
                "traceabilityGapCount", lowConfidenceCount,
                "consistencyIssueCount", reviewCount,
                "riskTags", riskTags
        );
    }

    private Map<String, Object> studentDetail(Map<String, Object> row) {
        Map<String, Object> base = toStudentRow(row);
        List<Map<String, Object>> dimensions = jdbc.queryForList(
                "select qd.question_no, qd.section_name, sir.score, sir.max_score, sir.confidence, " +
                        "sir.evidence_text, sir.comment_text, sir.needs_review " +
                        "from score_item_result sir " +
                        "left join question_definition qd on qd.id = sir.question_definition_id " +
                        "where sir.grading_run_id = :gradingRunId " +
                        "order by qd.sort_order",
                params("gradingRunId", row.get("grading_run_id"))
        );
        List<Map<String, Object>> mappedDimensions = new ArrayList<>();
        for (Map<String, Object> dimension : dimensions) {
            boolean needsReview = toInt(dimension.get("needs_review")) == 1;
            mappedDimensions.add(map(
                    "id", dimension.get("question_no"),
                    "name", dimension.get("section_name"),
                    "score", toDouble(dimension.get("score")),
                    "maxScore", toDouble(dimension.get("max_score")),
                    "confidence", toDouble(dimension.get("confidence")),
                    "evidence", dimension.get("evidence_text"),
                    "reasoning", dimension.get("comment_text"),
                    "matched", Arrays.asList("已从数据库 score_item_result 表读取区块得分。"),
                    "missing", needsReview ? Arrays.asList("该区块带有复核标记，建议教师抽查原始答题卡。") : Arrays.asList("暂无明显缺失项。"),
                    "improvement", needsReview ? "结合原始答题卡图像复核证据文本和扣分点。" : "可作为自动评分结果直接参考。"
            ));
        }
        double score = toDouble(base.get("score"));
        return map(
                "id", base.get("id"),
                "name", base.get("name"),
                "studentNumber", base.get("studentNumber"),
                "anonymousId", base.get("anonymousId"),
                "score", score,
                "percentileScore", score,
                "grade", base.get("grade"),
                "confidence", base.get("confidence"),
                "summary", row.get("summary_text"),
                "qualityFindings", base.get("riskTags"),
                "dimensions", mappedDimensions,
                "traceability", map(
                        "requirements", Arrays.asList("客观题识别", "填空题识别", "主观题评分", "综合建模题评分"),
                        "hldCoverage", Arrays.asList(map("requirement", "数据库评分结果落库", "status", "covered", "evidence", "final_result 与 score_item_result 均已写入。")),
                        "lldCoverage", Arrays.asList(map("requirement", "前端详情字段映射", "status", "covered", "evidence", "后端已将区块得分映射为 dimensions。")),
                        "uncoveredRequirements", new ArrayList<>()
                ),
                "gates", Arrays.asList(map(
                        "name", "人工复核建议",
                        "passed", !"需复核".equals(base.get("gateStatus")),
                        "detail", base.get("gateStatus"),
                        "onFail", "review"
                )),
                "materials", map(
                        "documentCount", 1,
                        "wordCount", 0,
                        "imageCount", 1,
                        "roles", Arrays.asList("答题卡图像", "系统评分报告"),
                        "logs", Arrays.asList("来源：validation-run/system-reports", "已落库为演示任务 " + DEMO_TASK_ID)
                )
        );
    }

    private Map<String, Object> demoRubric() {
        return map(
                "id", "answer-card-rubric-v1",
                "name", "软件需求答题卡评分规则",
                "version", "v1.0",
                "source", "template_copy",
                "status", "in_use",
                "updatedAt", "2026-04-18 09:30",
                "description", "按单选、判断、填空、简答、综合建模五个区块聚合评分。",
                "warnings", new ArrayList<>(),
                "totalScore", 100,
                "dimensions", Arrays.asList(
                        map("id", "single_choice", "name", "单项选择题", "maxScore", 20, "description", "10题，每题2分。"),
                        map("id", "true_false", "name", "判断题", "maxScore", 10, "description", "10题，每题1分。"),
                        map("id", "fill_blank", "name", "填空题", "maxScore", 10, "description", "5题，每题2分。"),
                        map("id", "short_answer", "name", "简答题", "maxScore", 20, "description", "按要点覆盖情况评分。"),
                        map("id", "comprehensive", "name", "综合建模题", "maxScore", 40, "description", "检查用例图、E-R图、DFD等综合表达。")
                ),
                "yaml", "rubric_id: answer-card-v1\ntotal_score: 100\n"
        );
    }

    private Map<String, Object> demoExportTemplate() {
        return map(
                "id", "answer-card-export-template-v1",
                "name", "答题卡联调成绩导出模板",
                "version", "v1.0",
                "status", "in_use",
                "fileNameRule", "{课程名称}-{任务名称}-{日期}.xlsx",
                "updatedAt", "2026-04-18 09:40",
                "sheets", Arrays.asList(
                        map("id", "summary", "name", "成绩总表", "columns", Arrays.asList(
                                map("id", "studentNumber", "label", "学号", "enabled", true),
                                map("id", "name", "label", "姓名", "enabled", true),
                                map("id", "score", "label", "总分", "enabled", true),
                                map("id", "review", "label", "复核状态", "enabled", true)
                        )),
                        map("id", "details", "name", "区块得分", "columns", Arrays.asList(
                                map("id", "section", "label", "题型区块", "enabled", true),
                                map("id", "score", "label", "得分", "enabled", true),
                                map("id", "evidence", "label", "评分证据", "enabled", true)
                        ))
                )
        );
    }

    private Map<String, Object> demoWorkspace(String status, String message) {
        return map(
                "rootPath", "database/answer_card_demo_seed.sql",
                "rawPath", "answer-card/workspace/validation-run/system-reports",
                "irPath", "answer-card/workspace/validation-run/system-extracted",
                "scoresPath", "MySQL.homework_grader.final_result",
                "reportsPath", "MySQL.homework_grader.score_item_result",
                "status", status,
                "lastCheckedAt", "2026-04-18 10:15",
                "lastMessage", message
        );
    }

    private Map<String, Object> exportRecord() {
        return map(
                "id", "answer-card-export-demo-1",
                "createdAt", "2026-04-18 10:20",
                "fileName", "软件需求分析-答题卡评分联调测试-2026-04-18.xlsx",
                "templateVersion", "v1.0",
                "status", "completed",
                "warnings", Arrays.asList("3 个样本带有人工复核建议。")
        );
    }

    private void ensureDemoTask(String taskId) throws FileNotFoundException {
        if (!DEMO_TASK_ID.equals(taskId)) {
            throw new FileNotFoundException("未知任务：" + taskId);
        }
    }

    private String grade(double score) {
        if (score >= 85) return "优秀";
        if (score >= 70) return "良好";
        if (score >= 60) return "及格";
        return "待关注";
    }

    private String formatDate(Object value) {
        if (value == null) return "";
        if (value instanceof Timestamp) {
            return ((Timestamp) value).toLocalDateTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
        }
        return String.valueOf(value);
    }

    private int toInt(Object value) {
        if (value == null) return 0;
        if (value instanceof Number) return ((Number) value).intValue();
        return Integer.parseInt(String.valueOf(value));
    }

    private double toDouble(Object value) {
        if (value == null) return 0;
        if (value instanceof BigDecimal) return ((BigDecimal) value).doubleValue();
        if (value instanceof Number) return ((Number) value).doubleValue();
        return Double.parseDouble(String.valueOf(value));
    }

    private MapSqlParameterSource params(Object... values) {
        MapSqlParameterSource params = new MapSqlParameterSource();
        for (int i = 0; i < values.length; i += 2) {
            params.addValue(String.valueOf(values[i]), values[i + 1]);
        }
        return params;
    }

    private Map<String, Object> map(Object... values) {
        Map<String, Object> map = new HashMap<>();
        for (int i = 0; i < values.length; i += 2) {
            map.put(String.valueOf(values[i]), values[i + 1]);
        }
        return map;
    }
}
