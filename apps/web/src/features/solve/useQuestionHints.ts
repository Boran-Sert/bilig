/**
 * Sorunun ipucunu sunucudan isteyip bulunan ipucunu çağırana verir.
 */
import { useState } from "react";
import { getProblemMessage } from "../../lib/api/problem";
import { useHint } from "./api";

/**
 * İpucu isteğinin bekleme ve hata durumunu tutar.
 */
export function useQuestionHints() {
  const hint = useHint();
  const [error, setError] = useState<string | null>(null);

  /** Verilen soru için ipucu ister; gelen ipucunu onHint ile iletir. */
  function requestHint(questionId: number, onHint: (hintText: string) => void) {
    if (hint.isPending) {
      return;
    }

    setError(null);
    hint.mutate(questionId, {
      /** Gelen ipucu metnini çağırana verir. */
      onSuccess: (response) => onHint(response.hint),
      /** Sunucu mesajını ya da genel hata metnini saklar. */
      onError: (failure) => setError(getProblemMessage(failure)),
    });
  }

  /** Başka soruya geçilirken hatayı ve bekleyen isteği temizler. */
  function reset() {
    setError(null);
    hint.reset();
  }

  return { error, isPending: hint.isPending, requestHint, reset };
}
