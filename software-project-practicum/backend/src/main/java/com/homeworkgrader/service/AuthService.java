package com.homeworkgrader.service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {
    public static final String SESSION_USER_ID = "AUTH_USER_ID";

    private final NamedParameterJdbcTemplate jdbc;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public AuthService(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Map<String, Object> authenticate(String username, String password) {
        if (username == null || username.trim().isEmpty() || password == null || password.isEmpty()) {
            return null;
        }

        Map<String, Object> user = findByUsername(username.trim());
        if (user == null || !isEnabled(user)) {
            return null;
        }

        String hash = String.valueOf(user.get("password_hash"));
        if (!passwordEncoder.matches(password, hash)) {
            return null;
        }

        jdbc.update(
                "update auth_user set last_login_at = :lastLoginAt where id = :id",
                new MapSqlParameterSource()
                        .addValue("lastLoginAt", LocalDateTime.now())
                        .addValue("id", user.get("id"))
        );
        return toUserDto(user);
    }

    public Map<String, Object> findSessionUser(Object userId) {
        if (userId == null) {
            return null;
        }
        List<Map<String, Object>> users = jdbc.queryForList(
                "select id, username, display_name, user_type, teacher_id, student_id, status " +
                        "from auth_user where id = :id",
                new MapSqlParameterSource("id", userId)
        );
        if (users.isEmpty() || !isEnabled(users.get(0))) {
            return null;
        }
        return toUserDto(users.get(0));
    }

    public Map<String, Object> findByUsername(String username) {
        List<Map<String, Object>> users = jdbc.queryForList(
                "select id, username, password_hash, display_name, user_type, teacher_id, student_id, status " +
                        "from auth_user where username = :username",
                new MapSqlParameterSource("username", username)
        );
        return users.isEmpty() ? null : users.get(0);
    }

    private boolean isEnabled(Map<String, Object> user) {
        Object status = user.get("status");
        return status instanceof Number && ((Number) status).intValue() == 1;
    }

    private Map<String, Object> toUserDto(Map<String, Object> user) {
        Map<String, Object> dto = new HashMap<>();
        dto.put("id", String.valueOf(user.get("id")));
        dto.put("username", user.get("username"));
        dto.put("name", user.get("display_name"));
        dto.put("role", user.get("user_type"));
        dto.put("teacherId", user.get("teacher_id"));
        dto.put("studentId", user.get("student_id"));
        return dto;
    }
}
