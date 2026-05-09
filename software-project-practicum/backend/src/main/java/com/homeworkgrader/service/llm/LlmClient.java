package com.homeworkgrader.service.llm;

public interface LlmClient {
    String generateJson(String systemPrompt, String userPrompt);
}
