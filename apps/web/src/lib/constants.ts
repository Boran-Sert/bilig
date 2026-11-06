/**
 * Arayüzde değişmeyen değerleri tutar.
 * Parola sınırları core servisindeki AppConstants ile aynı olmalıdır.
 */

export const ROUTES = {
  landing: "/",
  home: "/panel",
  login: "/login",
  register: "/register",
  adminSources: "/admin/sources",
  adminReview: "/admin/review",
  tests: "/tests",
  solve: "/tests/:testId/solve",
  testResult: "/sessions/:sessionId/result",
  sessionReview: "/sessions/:sessionId/review",
} as const;

export const HTTP_STATUS_UNAUTHORIZED = 401;

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

export const MARKDOWN_ALLOWED_TAGS = [
  "p",
  "br",
  "em",
  "strong",
  "u",
  "ul",
  "ol",
  "li",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
];

export const SOURCES_POLL_INTERVAL_MS = 3000;
export const SOURCES_PAGE_SIZE = 20;
export const UPLOAD_SOURCE_KINDS = ["TEXTBOOK", "TEST", "QUESTION_BANK", "ANSWER_KEY"] as const;
export const ANSWER_KEY_LIST_SIZE = 100;
