package com.homeworkgrader.config;

import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "grader")
public class GraderProperties {
    private Path workspaceRoot;
    private Python python = new Python();

    public Path getWorkspaceRoot() {
        return workspaceRoot;
    }

    public void setWorkspaceRoot(Path workspaceRoot) {
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
        private Path workingDirectory;
        private String preprocessScript;
        private String gradingScript;
        private String exportScript;

        public String getExecutable() {
            return executable;
        }

        public void setExecutable(String executable) {
            this.executable = executable;
        }

        public Path getWorkingDirectory() {
            return workingDirectory;
        }

        public void setWorkingDirectory(Path workingDirectory) {
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
    }
}
