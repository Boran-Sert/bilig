/**
 * Girişten sonra kullanıcının döneceği sayfayı belirler.
 */
import { ROUTES } from "../../lib/constants";

/**
 * Yönlendirme durumundaki uygulama içi adresi döndürür; yoksa ana sayfayı.
 * @param state RequireAuth'un yönlendirirken bıraktığı durum.
 * @returns Uygulama içi dönüş adresi.
 */
export function getReturnPath(state: unknown): string {
  const from = (state as { from?: { pathname?: unknown; search?: unknown } } | null)?.from;
  const pathname = from?.pathname;

  if (typeof pathname !== "string" || !pathname.startsWith("/") || pathname.startsWith("//")) {
    return ROUTES.home;
  }

  return typeof from?.search === "string" ? `${pathname}${from.search}` : pathname;
}
