package com.homeworkgrader.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.repository.CrudJdbcRepository;
import com.homeworkgrader.util.Maps;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.springframework.web.multipart.MultipartFile;
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

    public Long createFromFile(Long questionId, MultipartFile file) throws IOException {
        String fileName = file.getOriginalFilename() == null ? "standard-answer.txt" : file.getOriginalFilename();
        String answerText = extractAnswerText(fileName, file);
        if (answerText == null || answerText.trim().isEmpty()) {
            throw new IllegalArgumentException("上传文件未解析出标准答案文本。");
        }
        Map<String, Object> request = new HashMap<>();
        request.put("answer_text", answerText.trim());
        try {
            return create(questionId, request);
        } catch (JsonProcessingException ex) {
            throw new IOException("保存标准答案失败：" + ex.getMessage(), ex);
        }
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

    private String extractAnswerText(String fileName, MultipartFile file) throws IOException {
        String lowerName = fileName.toLowerCase();
        if (lowerName.endsWith(".docx")) {
            return extractDocxText(file);
        }
        if (lowerName.endsWith(".pdf")) {
            throw new IllegalArgumentException("暂不支持直接解析 PDF 标准答案，请上传 .docx、.txt、.md、.json、.yaml 或 .csv 文件。");
        }
        return new String(file.getBytes(), StandardCharsets.UTF_8);
    }

    private String extractDocxText(MultipartFile file) throws IOException {
        try (InputStream input = file.getInputStream();
             ZipInputStream zip = new ZipInputStream(input, StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if ("word/document.xml".equals(entry.getName())) {
                    ByteArrayOutputStream output = new ByteArrayOutputStream();
                    byte[] buffer = new byte[8192];
                    int read;
                    while ((read = zip.read(buffer)) != -1) {
                        output.write(buffer, 0, read);
                    }
                    return xmlToText(new String(output.toByteArray(), StandardCharsets.UTF_8));
                }
            }
        }
        throw new IllegalArgumentException("未在 .docx 文件中找到正文内容。");
    }

    private String xmlToText(String xml) {
        String withBreaks = xml
                .replaceAll("</w:p>", "\n")
                .replaceAll("</w:tr>", "\n")
                .replaceAll("</w:tc>", "\t");
        return withBreaks
                .replaceAll("<[^>]+>", "")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replace("&quot;", "\"")
                .replace("&apos;", "'")
                .replaceAll("[\\t ]+\\n", "\n")
                .replaceAll("\\n{3,}", "\n\n")
                .trim();
    }
}
