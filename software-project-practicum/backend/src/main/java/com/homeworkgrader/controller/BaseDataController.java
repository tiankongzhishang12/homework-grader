package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.service.OrganizationService;
import com.homeworkgrader.util.Maps;
import javax.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class BaseDataController {
    private final CrudJdbcRepository repository;
    private final OrganizationService organizationService;

    public BaseDataController(CrudJdbcRepository repository, OrganizationService organizationService) {
        this.repository = repository;
        this.organizationService = organizationService;
    }

    @GetMapping("/org/tree")
    public ApiResponse<?> orgTree() {
        return ApiResponse.ok(organizationService.tree());
    }

    @GetMapping("/teachers")
    public ApiResponse<?> teachers() {
        return ApiResponse.ok(repository.list("teacher"));
    }

    @PostMapping("/teachers")
    public ApiResponse<?> createTeacher(@Valid @RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", repository.insert("teacher", request)));
    }

    @GetMapping("/students")
    public ApiResponse<?> students() {
        return ApiResponse.ok(repository.list("student"));
    }

    @PostMapping("/students/import")
    public ApiResponse<?> importStudent(@Valid @RequestBody Map<String, Object> request) {
        return ApiResponse.ok(Maps.of("id", repository.insert("student", request)));
    }
}
