/**
 * RFC 9457 Problem Details yanıtlarını kullanıcıya gösterilecek mesaja dönüştürür.
 */
import i18n from "../i18n";

/**
 * Sunucunun doğrulama hatasında bildirdiği tek bir alan hatasını tanımlar.
 */
export interface FieldViolation {
  field: string;
  message: string;
}

/**
 * API'nin Problem Details hata yanıtındaki alanları tanımlar.
 */
interface ProblemDetails {
  code?: string;
  detail?: string;
  title?: string;
  errors?: unknown;
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
 * Değerin geçerli bir alan hatası olup olmadığını kontrol eder.
 * @param value Kontrol edilecek değer.
 * @returns Alan adı ve mesajı metinse true.
 */
function isFieldViolation(value: unknown): value is FieldViolation {
  return (
    isProblemDetails(value) &&
    typeof (value as FieldViolation).field === "string" &&
    typeof (value as FieldViolation).message === "string"
  );
}

/**
 * API'nin hata yanıtını HTTP durumuyla birlikte taşır.
 */
export class ApiError extends Error {
  readonly problem: ProblemDetails;
  readonly status: number;

  /**
   * Hata gövdesinden ve HTTP durumundan hata nesnesi oluşturur.
   * @param body Sunucunun döndürdüğü hata gövdesi.
   * @param status HTTP durum kodu.
   */
  constructor(body: unknown, status: number) {
    const problem = isProblemDetails(body) ? body : {};
    super(problem.code ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.problem = problem;
    this.status = status;
  }
}

/**
 * Hatadaki sunucu alan hatalarını döndürür.
 * @param error İşlenecek hata.
 * @returns Alan hataları; yoksa boş liste.
 */
export function getFieldErrors(error: unknown): FieldViolation[] {
  if (!(error instanceof ApiError) || !Array.isArray(error.problem.errors)) {
    return [];
  }

  return error.problem.errors.filter(isFieldViolation);
}

/**
 * API hatasını kullanıcıya gösterilecek bir mesaja dönüştürür.
 * @param error İşlenecek hata.
 * @returns Kullanıcıya gösterilecek hata mesajı.
 */
export function getProblemMessage(error: unknown): string {
  const problem = error instanceof ApiError ? error.problem : error;

  if (isProblemDetails(problem) && !(problem instanceof Error)) {
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

  if (error instanceof ApiError) {
    return i18n.t("errors.unknown");
  }

  if (error instanceof Error) {
    return error.message;
  }

  return i18n.t("errors.unknown");
}
