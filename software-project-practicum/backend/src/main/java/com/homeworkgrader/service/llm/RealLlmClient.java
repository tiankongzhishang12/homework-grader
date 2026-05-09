package com.homeworkgrader.service.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homeworkgrader.config.RubricCompilerProperties;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class RealLlmClient implements LlmClient {
    private final RubricCompilerProperties properties;
    private final ObjectMapper objectMapper;

    public RealLlmClient(RubricCompilerProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Override
    public String generateJson(String systemPrompt, String userPrompt) {
        if (isBlank(properties.getApiKey())) {
            throw new IllegalStateException("Rubric compiler API key is not configured. Set RUBRIC_LLM_API_KEY.");
        }
        if (isBlank(properties.getBaseUrl()) || isBlank(properties.getModel())) {
            throw new IllegalStateException("Rubric compiler model service is not configured.");
        }

        int attempts = Math.max(1, properties.getMaxRetries() + 1);
        RuntimeException last = null;
        for (int attempt = 1; attempt <= attempts; attempt++) {
            Instant started = Instant.now();
            try {
                String result = callChatCompletions(systemPrompt, userPrompt);
                long elapsed = java.time.Duration.between(started, Instant.now()).toMillis();
                System.out.println("Rubric compile LLM call succeeded model=" + properties.getModel() + " elapsedMs=" + elapsed);
                return result;
            } catch (RuntimeException ex) {
                last = ex;
                long elapsed = java.time.Duration.between(started, Instant.now()).toMillis();
                System.out.println("Rubric compile LLM call failed attempt=" + attempt + " model=" + properties.getModel() + " elapsedMs=" + elapsed + " error=" + abbreviate(ex.getMessage(), 180));
            }
        }
        throw last == null ? new IllegalStateException("Rubric compiler model call failed.") : last;
    }

    private String callChatCompletions(String systemPrompt, String userPrompt) {
        try {
            URL url = new URL(normalizeBaseUrl(properties.getBaseUrl()) + "/chat/completions");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            int timeoutMillis = Math.max(1, properties.getTimeoutSeconds()) * 1000;
            connection.setConnectTimeout(timeoutMillis);
            connection.setReadTimeout(timeoutMillis);
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("Authorization", "Bearer " + properties.getApiKey());

            Map<String, Object> payload = new HashMap<>();
            payload.put("model", properties.getModel());
            payload.put("temperature", 0.1);
            payload.put("max_tokens", 4096);
            payload.put("messages", java.util.Arrays.asList(
                    message("system", systemPrompt),
                    message("user", userPrompt)
            ));
            byte[] body = objectMapper.writeValueAsBytes(payload);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int status = connection.getResponseCode();
            String response = read(status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream());
            if (status < 200 || status >= 300) {
                throw new IllegalStateException("Rubric compiler model service returned HTTP " + status + ": " + abbreviate(response, 240));
            }
            JsonNode root = objectMapper.readTree(response);
            JsonNode content = root.path("choices").path(0).path("message").path("content");
            if (content.isMissingNode() || isBlank(content.asText())) {
                throw new IllegalStateException("Rubric compiler model returned empty content.");
            }
            return content.asText();
        } catch (Exception ex) {
            if (ex instanceof RuntimeException) {
                throw (RuntimeException) ex;
            }
            throw new IllegalStateException("Rubric compiler model call failed: " + ex.getMessage(), ex);
        }
    }

    private Map<String, String> message(String role, String content) {
        Map<String, String> message = new HashMap<>();
        message.put("role", role);
        message.put("content", content);
        return message;
    }

    private String read(InputStream input) throws Exception {
        if (input == null) {
            return "";
        }
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private String normalizeBaseUrl(String baseUrl) {
        String normalized = baseUrl.trim();
        return normalized.endsWith("/") ? normalized.substring(0, normalized.length() - 1) : normalized;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String abbreviate(String value, int max) {
        if (value == null) {
            return "";
        }
        return value.length() <= max ? value : value.substring(0, max) + "...";
    }
}
