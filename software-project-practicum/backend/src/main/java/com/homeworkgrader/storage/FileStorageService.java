package com.homeworkgrader.storage;

import com.homeworkgrader.config.GraderProperties;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.StandardCopyOption;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class FileStorageService {
    private final Path workspaceRoot;

    public FileStorageService(GraderProperties properties) {
        this.workspaceRoot = properties.getWorkspaceRoot().toAbsolutePath().normalize();
    }

    public StoredFile saveSubmissionFile(Long assessmentId, Long studentId, MultipartFile file) throws IOException {
        String originalName = sanitize(file.getOriginalFilename() == null ? "submission.bin" : file.getOriginalFilename());
        Path relativePath = workspaceRoot.getFileSystem().getPath("raw", "assessment-" + assessmentId, "student-" + studentId, originalName);
        Path target = workspaceRoot.resolve(relativePath).normalize();
        if (!target.startsWith(workspaceRoot)) {
            throw new IOException("非法文件路径");
        }
        Files.createDirectories(target.getParent());
        file.transferTo(target);
        return new StoredFile(relativePath.toString().replace('\\', '/'), originalName, Files.size(target), sha256(target));
    }

    public RawWorkspaceFile copyToRawWorkspace(String sourceRelativePath, String studentNo, String studentName, String fileName) throws IOException {
        String safeStudentNo = sanitizePathPart(studentNo);
        String safeStudentName = sanitizePathPart(isBlank(studentName) ? "student" : studentName);
        String safeFileName = sanitize(fileName == null ? "submission.bin" : fileName);
        Path rawRoot = workspaceRoot.resolve("raw").normalize();
        Path studentDir = rawRoot.resolve(safeStudentNo + "_" + safeStudentName).normalize();
        if (!rawRoot.startsWith(workspaceRoot) || !studentDir.startsWith(rawRoot)) {
            throw new IOException("非法 raw workspace 路径");
        }
        Path source = resolve(sourceRelativePath);
        Path target = studentDir.resolve(safeFileName).normalize();
        if (!target.startsWith(studentDir)) {
            throw new IOException("非法 raw workspace 文件路径");
        }
        Files.createDirectories(studentDir);
        boolean overwritten = Files.exists(target);
        Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
        String relativePath = workspaceRoot.relativize(target).toString().replace('\\', '/');
        String message = overwritten
                ? "Copied to grading raw workspace, overwriting an existing file with the same name."
                : "Copied to grading raw workspace.";
        return new RawWorkspaceFile(relativePath, overwritten, message);
    }

    public Path resolve(String relativePath) throws IOException {
        Path resolved = workspaceRoot.resolve(relativePath).normalize();
        if (!resolved.startsWith(workspaceRoot) || !Files.exists(resolved)) {
            throw new IOException("文件不存在：" + relativePath);
        }
        return resolved;
    }

    public Path reportsRoot() throws IOException {
        Path reports = workspaceRoot.resolve("reports").normalize();
        Files.createDirectories(reports);
        return reports;
    }

    private String sanitize(String name) {
        return name.replaceAll("[\\\\/:*?\"<>|]", "_");
    }

    private String sanitizePathPart(String value) {
        String sanitized = sanitize(value == null ? "" : value.trim());
        return sanitized.isEmpty() ? "student" : sanitized;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String sha256(Path path) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = Files.newInputStream(path);
                 DigestInputStream digestInput = new DigestInputStream(input, digest)) {
                byte[] buffer = new byte[8192];
                while (digestInput.read(buffer) != -1) {
                    // DigestInputStream updates the hash as bytes are read.
                }
            }
            return toHex(digest.digest());
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException(ex);
        }
    }

    private String toHex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            builder.append(String.format("%02x", b));
        }
        return builder.toString();
    }

    public static class StoredFile {
        private final String relativePath;
        private final String fileName;
        private final long size;
        private final String sha256;

        public StoredFile(String relativePath, String fileName, long size, String sha256) {
            this.relativePath = relativePath;
            this.fileName = fileName;
            this.size = size;
            this.sha256 = sha256;
        }

        public String getRelativePath() {
            return relativePath;
        }

        public String getFileName() {
            return fileName;
        }

        public long getSize() {
            return size;
        }

        public String getSha256() {
            return sha256;
        }
    }

    public static class RawWorkspaceFile {
        private final String relativePath;
        private final boolean overwritten;
        private final String message;

        public RawWorkspaceFile(String relativePath, boolean overwritten, String message) {
            this.relativePath = relativePath;
            this.overwritten = overwritten;
            this.message = message;
        }

        public String getRelativePath() {
            return relativePath;
        }

        public boolean isOverwritten() {
            return overwritten;
        }

        public String getMessage() {
            return message;
        }
    }
}
