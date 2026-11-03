/**
 * Arayüzde değişmeyen değerleri tutar.
 * Parola sınırları core servisindeki AppConstants ile aynı olmalıdır.
 */

export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  adminSources: "/admin/sources",
} as const;

export const HTTP_STATUS_UNAUTHORIZED = 401;

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

export const SOURCES_POLL_INTERVAL_MS = 3000;
export const SOURCES_PAGE_SIZE = 20;
