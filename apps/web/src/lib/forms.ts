/**
 * Sunucu doğrulama hatalarını react-hook-form alanlarına aktarır.
 */
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { getFieldErrors } from "./api/problem";

/**
 * Sunucunun bildirdiği alan hatalarını formdaki aynı adlı alanlara yazar.
 * @param error Sunucudan gelen hata.
 * @param fields Formda bulunan alan adları.
 * @param setError Formun hata yazma fonksiyonu.
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  fields: readonly Path<T>[],
  setError: UseFormSetError<T>,
) {
  for (const violation of getFieldErrors(error)) {
    const field = fields.find((name) => name === violation.field);

    if (field) {
      setError(field, { type: "server", message: violation.message });
    }
  }
}
