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
import java.util.Properties;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.core.io.FileSystemResource;
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
        LlmSettings settings = resolveSettings();
        if (isBlank(settings.apiKey)) {
            throw new IllegalStateException("Rubric compiler API key is not configured. Set RUBRIC_LLM_API_KEY or openai.api_key in grader-config.yaml.");
        }
        if (isBlank(settings.baseUrl) || isBlank(settings.model)) {
            throw new IllegalStateException("Rubric compiler model service is not configured. Set RUBRIC_LLM_BASE_URL/RUBRIC_LLM_MODEL or openai.base_url/openai.model in grader-config.yaml.");
        }

        int attempts = Math.max(1, properties.getMaxRetries() + 1);
        RuntimeException last = null;
        for (int attempt = 1; attempt <= attempts; attempt++) {
            Instant started = Instant.now();
            try {
                String result = callChatCompletions(systemPrompt, userPrompt, settings);
                long elapsed = java.time.Duration.between(started, Instant.now()).toMillis();
                System.out.println("Rubric compile LLM call succeeded model=" + settings.model + " elapsedMs=" + elapsed);
                return result;
            } catch (RuntimeException ex) {
                last = ex;
                long elapsed = java.time.Duration.between(started, Instant.now()).toMillis();
                System.out.println("Rubric compile LLM call failed attempt=" + attempt + " model=" + settings.model + " elapsedMs=" + elapsed + " error=" + abbreviate(ex.getMessage(), 180));
            }
        }
        throw last == null ? new IllegalStateException("Rubric compiler model call failed.") : last;
    }

    private String callChatCompletions(String systemPrompt, String userPrompt, LlmSettings settings) {
        try {
            URL url = new URL(normalizeBaseUrl(settings.baseUrl) + "/chat/completions");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            int timeoutMillis = Math.max(1, properties.getTimeoutSeconds()) * 1000;
            connection.setConnectTimeout(timeoutMillis);
            connection.setReadTimeout(timeoutMillis);
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("Authorization", "Bearer " + settings.apiKey);

            Map<String, Object> payload = new HashMap<>();
            payload.put("model", settings.model);
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

    private LlmSettings resolveSettings() {
        Properties local = loadLocalConfig();
        String apiKey = firstNonBlank(properties.getApiKey(), local.getProperty("openai.api_key"));
        String baseUrl = firstNonBlank(properties.getBaseUrl(), local.getProperty("openai.base_url"));
        String model = firstNonBlank(properties.getModel(), local.getProperty("openai.model"));
        return new LlmSettings(apiKey, baseUrl, model);
    }

    private Properties loadLocalConfig() {
        if (isBlank(properties.getConfigPath())) {
            return new Properties();
        }
        FileSystemResource resource = new FileSystemResource(properties.getConfigPath());
        if (!resource.exists()) {
            return new Properties();
        }
        YamlPropertiesFactoryBean factory = new YamlPropertiesFactoryBean();
        factory.setResources(resource);
        Properties loaded = factory.getObject();
        return loaded == null ? new Properties() : loaded;
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

    private String firstNonBlank(String first, String second) {
        return isBlank(first) ? second : first;
    }

    private static class LlmSettings {
        private final String apiKey;
        private final String baseUrl;
        private final String model;

        private LlmSettings(String apiKey, String baseUrl, String model) {
            this.apiKey = apiKey;
            this.baseUrl = baseUrl;
            this.model = model;
        }
    }
}
