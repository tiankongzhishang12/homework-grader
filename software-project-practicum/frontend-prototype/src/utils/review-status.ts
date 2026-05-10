export type ReviewStatus = "AI_GENERATED" | "REVIEW_REQUIRED" | "CONFIRMED" | "ADJUSTED" | "PUBLISHED" | "UNKNOWN";

export const normalizeReviewStatus = (status?: string | null) => (status ?? "").trim().toUpperCase();

export const canonicalReviewStatus = (status?: string | null): ReviewStatus => {
  const normalized = normalizeReviewStatus(status);
  if (normalized === "NEEDS_REVIEW" || normalized === "REVIEW_REQUIRED") return "REVIEW_REQUIRED";
  if (normalized === "AI_GENERATED") return "AI_GENERATED";
  if (normalized === "CONFIRMED") return "CONFIRMED";
  if (normalized === "ADJUSTED") return "ADJUSTED";
  if (normalized === "PUBLISHED") return "PUBLISHED";
  return "UNKNOWN";
};

export const reviewStatusLabel = (status?: string | null) => {
  switch (canonicalReviewStatus(status)) {
    case "REVIEW_REQUIRED":
      return "待教师复核";
    case "AI_GENERATED":
      return "待教师确认";
    case "CONFIRMED":
      return "已确认";
    case "ADJUSTED":
      return "已调整";
    case "PUBLISHED":
      return "已发布";
    default:
      return "待确认";
  }
};

export const isReviewRequired = (status?: string | null) => canonicalReviewStatus(status) === "REVIEW_REQUIRED";

export const isPendingConfirmation = (status?: string | null) => canonicalReviewStatus(status) === "AI_GENERATED";

export const isConfirmedStatus = (status?: string | null) => {
  const canonical = canonicalReviewStatus(status);
  return canonical === "CONFIRMED" || canonical === "PUBLISHED";
};

export const isAdjustedStatus = (status?: string | null) => canonicalReviewStatus(status) === "ADJUSTED";

export const reviewStatusTone = (status?: string | null) => {
  switch (canonicalReviewStatus(status)) {
    case "CONFIRMED":
    case "PUBLISHED":
      return "status-badge--good";
    case "ADJUSTED":
    case "AI_GENERATED":
      return "status-badge--warn";
    case "REVIEW_REQUIRED":
    case "UNKNOWN":
    default:
      return "status-badge--risk";
  }
};

export const formatConfidence = (value?: number | null) => {
  if (value === null || value === undefined || value <= 0) {
    return "暂无置信度";
  }
  return Number(value).toFixed(2);
};

export const hasLowConfidence = (value?: number | null) => value !== null && value !== undefined && value > 0 && value < 0.8;
