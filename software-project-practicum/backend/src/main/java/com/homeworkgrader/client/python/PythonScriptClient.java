package com.homeworkgrader.client.python;

import com.homeworkgrader.config.GraderProperties;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.core.io.FileSystemResource;
import org.springframework.stereotype.Component;

@Component
public class PythonScriptClient {
    private final GraderProperties.Python python;

    public PythonScriptClient(GraderProperties properties) {
        this.python = properties.getPython();
    }

    public ScriptResult runPreprocess() throws IOException, InterruptedException {
        return run(python.getPreprocessScript(), null);
    }

    public ScriptResult runPreprocess(Path configPath) throws IOException, InterruptedException {
        return run(python.getPreprocessScript(), configPath);
    }

    public ScriptResult runGrading() throws IOException, InterruptedException {
        return run(python.getGradingScript(), null);
    }

    public ScriptResult runGrading(Path configPath) throws IOException, InterruptedException {
        return run(python.getGradingScript(), configPath);
    }

    public ScriptResult runExport() throws IOException, InterruptedException {
        // Legacy export script hook; no longer used by the formal Java grade export path.
        return run(python.getExportScript(), null);
    }

    public ScriptResult runExport(Path configPath) throws IOException, InterruptedException {
        // Legacy export script hook; no longer used by the formal Java grade export path.
        return run(python.getExportScript(), configPath);
    }

    private ScriptResult run(String script, Path overrideConfigPath) throws IOException, InterruptedException {
        Instant startedAt = Instant.now();
        List<String> command = new ArrayList<>();
        command.add(python.getExecutable());
        command.add(script);
        if (overrideConfigPath != null) {
            command.add("--config");
            command.add(overrideConfigPath.toString());
        } else if (python.getConfigPath() != null && !python.getConfigPath().trim().isEmpty()) {
            command.add("--config");
            command.add(python.getConfigPath().trim());
        }
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.directory(python.getWorkingDirectory().toAbsolutePath().normalize().toFile());
        Map<String, String> environment = builder.environment();
        environment.putIfAbsent("PYTHONIOENCODING", "utf-8");
        environment.putIfAbsent("PYTHONUTF8", "1");
        applyLocalOpenAiEnvironment(environment);
        Process process = builder.start();
        String stdout = readFully(process.getInputStream());
        String stderr = readFully(process.getErrorStream());
        int exitCode = process.waitFor();
        return new ScriptResult(script, startedAt, Instant.now(), exitCode, stdout, stderr);
    }

    private void applyLocalOpenAiEnvironment(Map<String, String> environment) {
        Properties local = loadLocalConfig();
        putIfPresent(environment, "OPENAI_API_KEY", local.getProperty("openai.api_key"));
        putIfPresent(environment, "OPENAI_BASE_URL", local.getProperty("openai.base_url"));
        putIfPresent(environment, "SCORING_MODEL", local.getProperty("openai.model"));
    }

    private void putIfPresent(Map<String, String> environment, String key, String value) {
        if (!environment.containsKey(key) && value != null && !value.trim().isEmpty()) {
            environment.put(key, value.trim());
        }
    }

    private Properties loadLocalConfig() {
        Path configPath = resolveDefaultConfigPath();
        if (configPath == null || !java.nio.file.Files.exists(configPath)) {
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
        if (java.nio.file.Files.exists(fromWorkingDirectory)) {
            return fromWorkingDirectory;
        }
        Path fromBackendDirectory = java.nio.file.Paths.get("").toAbsolutePath().resolve(configured).normalize();
        if (java.nio.file.Files.exists(fromBackendDirectory)) {
            return fromBackendDirectory;
        }
        Path repoRootConfig = java.nio.file.Paths.get("").toAbsolutePath().resolve("../../grader-config.yaml").normalize();
        return java.nio.file.Files.exists(repoRootConfig) ? repoRootConfig : fromWorkingDirectory;
    }

    private String readFully(InputStream inputStream) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = inputStream.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        return decodeProcessOutput(output.toByteArray());
    }

    private String decodeProcessOutput(byte[] bytes) {
        String utf8 = new String(bytes, StandardCharsets.UTF_8);
        if (!looksLikeMojibake(utf8)) {
            return utf8;
        }
        return new String(bytes, Charset.forName("GB18030"));
    }

    private boolean looksLikeMojibake(String text) {
        if (text == null || text.isEmpty()) {
            return false;
        }
        if (text.indexOf('\uFFFD') >= 0) {
            return true;
        }
        int suspicious = 0;
        String markers = "����锟斤拷鐠閺闂";
        for (int i = 0; i < text.length(); i++) {
            if (markers.indexOf(text.charAt(i)) >= 0) {
                suspicious++;
            }
        }
        return suspicious >= 2;
    }

    public static class ScriptResult {
        private final String script;
        private final Instant startedAt;
        private final Instant finishedAt;
        private final int exitCode;
        private final String stdout;
        private final String stderr;

        public ScriptResult(String script, Instant startedAt, Instant finishedAt, int exitCode, String stdout, String stderr) {
            this.script = script;
            this.startedAt = startedAt;
            this.finishedAt = finishedAt;
            this.exitCode = exitCode;
            this.stdout = stdout;
            this.stderr = stderr;
        }

        public boolean success() {
            return exitCode == 0;
        }

        public String getScript() {
            return script;
        }

        public Instant getStartedAt() {
            return startedAt;
        }

        public Instant getFinishedAt() {
            return finishedAt;
        }

        public int getExitCode() {
            return exitCode;
        }

        public String getStdout() {
            return stdout;
        }

        public String getStderr() {
            return stderr;
        }
    }
}
