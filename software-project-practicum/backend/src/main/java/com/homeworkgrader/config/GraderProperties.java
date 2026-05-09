package com.homeworkgrader.config;

import java.nio.file.Path;
import java.nio.file.Paths;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "grader")
public class GraderProperties {
    private String workspaceRoot;
    private Python python = new Python();

    public Path getWorkspaceRoot() {
        return Paths.get(workspaceRoot);
    }

    public void setWorkspaceRoot(String workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
    }

    public Python getPython() {
        return python;
    }

    public void setPython(Python python) {
        this.python = python;
    }

    public static class Python {
        private String executable;
        private String workingDirectory;
        private String preprocessScript;
        private String gradingScript;
        private String exportScript;
        private String configPath;

        public String getExecutable() {
            return executable;
        }

        public void setExecutable(String executable) {
            this.executable = executable;
        }

        public Path getWorkingDirectory() {
            return Paths.get(workingDirectory);
        }

        public void setWorkingDirectory(String workingDirectory) {
            this.workingDirectory = workingDirectory;
        }

        public String getPreprocessScript() {
            return preprocessScript;
        }

        public void setPreprocessScript(String preprocessScript) {
            this.preprocessScript = preprocessScript;
        }

        public String getGradingScript() {
            return gradingScript;
        }

        public void setGradingScript(String gradingScript) {
            this.gradingScript = gradingScript;
        }

        public String getExportScript() {
            return exportScript;
        }

        public void setExportScript(String exportScript) {
            this.exportScript = exportScript;
        }

        public String getConfigPath() {
            return configPath;
        }

        public void setConfigPath(String configPath) {
            this.configPath = configPath;
        }
    }
}
