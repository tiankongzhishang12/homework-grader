package com.homeworkgrader.service;

import com.homeworkgrader.config.GraderProperties;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Service;

@Service
public class GraderRuntimeConfigService {
    private final GraderProperties.Python python;
    private final Path workspaceRoot;

    public GraderRuntimeConfigService(GraderProperties properties) {
        this.python = properties.getPython();
        this.workspaceRoot = properties.getWorkspaceRoot().toAbsolutePath().normalize();
    }

    public Path createRuntimeConfig(Long assessmentId, Path rubricYamlPath) {
        Path rubricPath = rubricYamlPath.toAbsolutePath().normalize();
        ensureInsideWorkspace(rubricPath);
        Path configPath = workspaceRoot.resolve("runtime/config/assessment-" + assessmentId + "-grader-config.yaml").normalize();
        ensureInsideWorkspace(configPath);

        Properties local = loadLocalConfig();
        String model = firstNonBlank(local.getProperty("openai.model"), "gpt-5.4");
        String baseUrl = firstNonBlank(local.getProperty("openai.base_url"), "");
        StringBuilder yaml = new StringBuilder();
        yaml.append("grading:\n");
        yaml.append("  workspace_path: \"").append(escape(workspaceRoot.toString())).append("\"\n");
        yaml.append("  rubric_path: \"").append(escape(rubricPath.toString())).append("\"\n");
        yaml.append("  workers: 3\n");
        yaml.append("\n");
        yaml.append("openai:\n");
        yaml.append("  model: \"").append(escape(model)).append("\"\n");
        if (!baseUrl.trim().isEmpty()) {
            yaml.append("  base_url: \"").append(escape(baseUrl)).append("\"\n");
        }

        try {
            Files.createDirectories(configPath.getParent());
            Files.write(configPath, yaml.toString().getBytes(StandardCharsets.UTF_8));
        } catch (IOException ex) {
            throw new IllegalStateException("运行时评分配置生成失败，请检查工作区权限。", ex);
        }
        return configPath;
    }

    private Properties loadLocalConfig() {
        Path configPath = resolveDefaultConfigPath();
        if (configPath == null || !Files.exists(configPath)) {
            return new Properties();
        }
        YamlPropertiesFactoryBean factory = new YamlPropertiesFactoryBean();
        factory.setResources(new FileSystemResource(configPath.toFile()));
        Properties loaded = factory.getObject();
        return loaded == null ? new Properties() : loaded;
    }

    private Path resolveDefaultConfigPath() {
        if (python.getConfigPath() == null || python.getConfigPath().trim().isEmpty()) {
            return null;
        }
        Path configured = java.nio.file.Paths.get(python.getConfigPath().trim());
        if (configured.isAbsolute()) {
            return configured.normalize();
        }
        Path fromWorkingDirectory = python.getWorkingDirectory().resolve(configured).toAbsolutePath().normalize();
        if (Files.exists(fromWorkingDirectory)) {
            return fromWorkingDirectory;
        }
        Path fromBackendDirectory = java.nio.file.Paths.get("").toAbsolutePath().resolve(configured).normalize();
        if (Files.exists(fromBackendDirectory)) {
            return fromBackendDirectory;
        }
        Path repoRootConfig = java.nio.file.Paths.get("").toAbsolutePath().resolve("../../grader-config.yaml").normalize();
        return Files.exists(repoRootConfig) ? repoRootConfig : fromWorkingDirectory;
    }

    private void ensureInsideWorkspace(Path path) {
        if (!path.startsWith(workspaceRoot)) {
            throw new IllegalStateException("运行时评分配置路径不在工作区内。");
        }
    }

    private String firstNonBlank(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }

    private String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
