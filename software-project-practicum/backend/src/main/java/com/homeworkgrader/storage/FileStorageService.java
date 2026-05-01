package com.homeworkgrader.storage;

import com.homeworkgrader.config.GraderProperties;
import java.io.IOException;
import java.io.InputStream;
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
}
