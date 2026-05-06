package com.homeworkgrader.controller;

import com.homeworkgrader.api.ApiResponse;
import com.homeworkgrader.service.AuthService;
import java.util.Map;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(
        originPatterns = {"http://localhost:*", "http://127.0.0.1:*"},
        allowCredentials = "true"
)
public class AuthController {
    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<?>> login(@RequestBody Map<String, Object> request, HttpServletRequest servletRequest) {
        String username = stringValue(request.get("username"));
        String password = stringValue(request.get("password"));
        Map<String, Object> user = authService.authenticate(username, password);
        if (user == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiResponse.error("用户名或密码错误。"));
        }

        HttpSession session = servletRequest.getSession(true);
        session.setAttribute(AuthService.SESSION_USER_ID, user.get("id"));
        return ResponseEntity.ok(ApiResponse.ok(user));
    }

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<?>> me(HttpSession session) {
        Map<String, Object> user = authService.findSessionUser(session.getAttribute(AuthService.SESSION_USER_ID));
        if (user == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiResponse.error("未登录或登录已过期。"));
        }
        return ResponseEntity.ok(ApiResponse.ok(user));
    }

    @PostMapping("/logout")
    public ApiResponse<?> logout(HttpSession session) {
        session.invalidate();
        return ApiResponse.ok(success());
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private Map<String, Object> success() {
        java.util.Map<String, Object> result = new java.util.HashMap<>();
        result.put("success", true);
        return result;
    }
}
