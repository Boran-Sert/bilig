/**
 * RFC 9457 Problem Details yanıtlarını kullanıcıya gösterilecek mesaja dönüştürür.
 */
import i18n from "../i18n";

/**
 * API'nin Problem Details hata yanıtındaki alanları tanımlar.
 */
interface ProblemDetails {
  code?: string;
  detail?: string;
  title?: string;
}

/**
 * Değerin null olmayan bir nesne olup olmadığını kontrol eder.
 * @param value Kontrol edilecek değer.
 * @returns Değer bir nesneyse true.
 */
function isProblemDetails(value: unknown): value is ProblemDetails {
  return typeof value === "object" && value !== null;
}

/**
 * API hatasını kullanıcıya gösterilecek bir mesaja dönüştürür.
 * @param error İşlenecek hata.
 * @returns Kullanıcıya gösterilecek hata mesajı.
 */
export function getProblemMessage(error: unknown): string {
  if (isProblemDetails(error)) {
    const problem = error;

    if (typeof problem.code === "string" && problem.code.length > 0) {
      return i18n.t(`errors.${problem.code}`, {
        ns: ["auth", "common"],
        defaultValue:
          (typeof problem.detail === "string" && problem.detail) ||
          (typeof problem.title === "string" && problem.title) ||
          problem.code,
      });
    }

    if (typeof problem.detail === "string" && problem.detail.length > 0) {
      return problem.detail;
    }

    if (typeof problem.title === "string" && problem.title.length > 0) {
      return problem.title;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return i18n.t("errors.unknown");
}
