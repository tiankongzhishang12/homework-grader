package com.homeworkgrader.client.python;

import com.homeworkgrader.config.GraderProperties;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class PythonScriptClient {
    private final GraderProperties.Python python;

    public PythonScriptClient(GraderProperties properties) {
        this.python = properties.getPython();
    }

    public ScriptResult runPreprocess() throws IOException, InterruptedException {
        return run(python.getPreprocessScript());
    }

    public ScriptResult runGrading() throws IOException, InterruptedException {
        return run(python.getGradingScript());
    }

    public ScriptResult runExport() throws IOException, InterruptedException {
        return run(python.getExportScript());
    }

    private ScriptResult run(String script) throws IOException, InterruptedException {
        Instant startedAt = Instant.now();
        List<String> command = new ArrayList<>();
        command.add(python.getExecutable());
        command.add(script);
        if (python.getConfigPath() != null && !python.getConfigPath().trim().isEmpty()) {
            command.add("--config");
            command.add(python.getConfigPath().trim());
        }
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.directory(python.getWorkingDirectory().toAbsolutePath().normalize().toFile());
        Map<String, String> environment = builder.environment();
        environment.putIfAbsent("PYTHONIOENCODING", "utf-8");
        environment.putIfAbsent("PYTHONUTF8", "1");
        Process process = builder.start();
        String stdout = readFully(process.getInputStream());
        String stderr = readFully(process.getErrorStream());
        int exitCode = process.waitFor();
        return new ScriptResult(script, startedAt, Instant.now(), exitCode, stdout, stderr);
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
