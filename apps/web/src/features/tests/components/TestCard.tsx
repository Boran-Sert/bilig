/**
 * Tek bir testi görsel alanı, ilerlemesi ve başlama ya da devam etme düğmesiyle gösterir.
 */
import { ImageIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import ActionButton from "../../../components/ActionButton";
import { Button } from "../../../components/ui/button";
import type { ExamSummary } from "../../solve/types";

interface TestCardProps {
  test: ExamSummary;
  onStart: (testId: number) => void;
}

/**
 * Testin durumuna göre başla, devam et düğmesini ya da tamamlandı etiketini çizer.
 * @param props Test özeti ve başlatma işlevi.
 * @returns Test kartı.
 */
export default function TestCard({ test, onStart }: TestCardProps) {
  const { t } = useTranslation("test");
  const hasProgress = test.answeredCount > 0 || test.sessionId !== null;
  const isCompleted = test.status === "COMPLETED";
  const progressPercent =
    test.questionCount > 0 ? Math.round((test.answeredCount / test.questionCount) * 100) : 0;

  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md">
      <div
        role="img"
        aria-label={t("testList.coverAlt")}
        className="flex h-40 items-center justify-center bg-navy-soft text-navy-strong/50"
      >
        <ImageIcon className="size-8" aria-hidden="true" />
      </div>

      <div className="flex flex-1 flex-col justify-between gap-5 p-6">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-heading">{test.title}</h2>
          <p className="text-sm text-muted-foreground">
            {hasProgress
              ? t("testList.answeredCount", {
                  count: test.answeredCount,
                  total: test.questionCount,
                })
              : t("testList.questionCount", { count: test.questionCount })}
          </p>
        </div>

        {hasProgress && !isCompleted && (
          <div className="h-2 overflow-hidden rounded-full bg-navy-soft">
            <div className="h-full rounded-full bg-info" style={{ width: `${progressPercent}%` }} />
          </div>
        )}

        <div>
          {isCompleted ? (
            <span className="inline-flex rounded-full bg-success-soft px-3 py-1 text-xs font-medium text-success">
              {t("testList.completed")}
            </span>
          ) : hasProgress ? (
            <ActionButton onClick={() => onStart(test.id)}>{t("testList.resume")}</ActionButton>
          ) : (
            <Button
              variant="outline"
              className="h-10 rounded-xl px-5"
              onClick={() => onStart(test.id)}
            >
              {t("testList.start")}
            </Button>
          )}
        </div>
      </div>
    </article>
  );
}
