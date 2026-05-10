export const normalizeReviewStatus = (status?: string | null) => (status ?? "").trim().toUpperCase();

export const reviewStatusLabel = (status?: string | null) => {
  switch (normalizeReviewStatus(status)) {
    case "NEEDS_REVIEW":
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

export const isReviewRequired = (status?: string | null) => {
  const normalized = normalizeReviewStatus(status);
  return normalized === "NEEDS_REVIEW" || normalized === "REVIEW_REQUIRED" || normalized === "AI_GENERATED";
};

export const reviewStatusTone = (status?: string | null) => {
  const normalized = normalizeReviewStatus(status);
  if (normalized === "CONFIRMED" || normalized === "PUBLISHED") return "status-badge--good";
  if (normalized === "ADJUSTED" || normalized === "AI_GENERATED") return "status-badge--warn";
  return "status-badge--risk";
};

export const formatConfidence = (value?: number | null) => {
  if (value === null || value === undefined || value <= 0) {
    return "暂无置信度";
  }
  return Number(value).toFixed(2);
};

export const hasLowConfidence = (value?: number | null) => value !== null && value !== undefined && value > 0 && value < 0.8;
