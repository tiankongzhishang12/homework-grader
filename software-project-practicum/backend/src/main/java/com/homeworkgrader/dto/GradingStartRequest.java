package com.homeworkgrader.dto;

import com.homeworkgrader.domain.GradingMode;

public class GradingStartRequest {
    private String mode;

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public GradingMode resolveMode() {
        if (mode == null || mode.trim().isEmpty()) {
            return GradingMode.INCREMENTAL;
        }
        try {
            GradingMode resolved = GradingMode.valueOf(mode.trim().toUpperCase());
            if (resolved == GradingMode.SELECTED) {
                throw new IllegalArgumentException("SELECTED mode is reserved and not implemented yet.");
            }
            return resolved;
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("Invalid grading mode: " + mode);
        }
    }
}
