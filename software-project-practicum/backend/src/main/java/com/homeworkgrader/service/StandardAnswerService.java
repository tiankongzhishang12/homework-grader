package com.homeworkgrader.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class StandardAnswerService {
    private final CrudJdbcRepository repository;
    private final ObjectMapper objectMapper;

    public StandardAnswerService(CrudJdbcRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    public Long create(Long questionId, Map<String, Object> request) throws JsonProcessingException {
        Object answerTextValue = request.get("answer_text");
        String answerText = answerTextValue == null ? null : String.valueOf(answerTextValue).trim();
        Object answerJson = request.get("answer_json");

        if ((answerText == null || answerText.isEmpty()) && answerJson == null) {
            throw new IllegalArgumentException("answer_text 和 answer_json 至少需要提供一个");
        }

        Map<String, Object> values = new HashMap<>();
        values.put("question_definition_id", questionId);
        if (answerText != null && !answerText.isEmpty()) {
            values.put("answer_text", answerText);
        }
        if (answerJson != null) {
            values.put("answer_json", normalizeJson(answerJson));
        }
        values.put("version_no", resolveVersionNo(questionId, request.get("version_no")));
        return repository.insert("standard_answer", values);
    }

    public List<Map<String, Object>> listByQuestion(Long questionId) {
        return repository.query(
                "select * from standard_answer where question_definition_id = :questionId order by version_no desc, id desc",
                Maps.of("questionId", questionId)
        );
    }

    public Map<String, Object> get(Long id) {
        return repository.get("standard_answer", id);
    }

    private Integer resolveVersionNo(Long questionId, Object requestedVersion) {
        if (requestedVersion != null) {
            if (requestedVersion instanceof Number) {
                return ((Number) requestedVersion).intValue();
            }
            return Integer.parseInt(String.valueOf(requestedVersion));
        }
        Integer maxVersion = repository.queryForInteger(
                "select coalesce(max(version_no), 0) from standard_answer where question_definition_id = :questionId",
                Maps.of("questionId", questionId)
        );
        return maxVersion + 1;
    }

    private String normalizeJson(Object answerJson) throws JsonProcessingException {
        if (answerJson instanceof String) {
            return (String) answerJson;
        }
        return objectMapper.writeValueAsString(answerJson);
    }
}
