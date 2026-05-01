package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class CourseController {
    private final CrudJdbcRepository repository;

    public CourseController(CrudJdbcRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/courses")
    public ApiResponse<?> courses() {
        return ApiResponse.ok(repository.list("course"));
    }

    @PostMapping("/courses")
    public ApiResponse<?> createCourse(@RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", repository.insert("course", request)));
    }

    @GetMapping("/course-offerings")
    public ApiResponse<?> courseOfferings() {
        return ApiResponse.ok(repository.list("course_offering"));
    }

    @PostMapping("/course-offerings")
    public ApiResponse<?> createCourseOffering(@RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", repository.insert("course_offering", request)));
    }

    @GetMapping("/teaching-classes/{id}/students")
    public ApiResponse<?> teachingClassStudents(@PathVariable Long id) {
        return ApiResponse.ok(repository.listBy("teaching_class_student", "teaching_class_id", id));
    }
}
