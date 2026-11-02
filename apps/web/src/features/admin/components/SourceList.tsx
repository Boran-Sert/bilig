/**
 * Kaynak dosyalarının durumunu ve 8 adım ilerlemesini tablo olarak gösterir.
 */
import { useTranslation } from "react-i18next";
import type { SourceListItem } from "../types";

interface SourceListProps {
  items: SourceListItem[];
}

const TOTAL_SEGMENTS = 8;

/**
 * Dosyanın adımına göre segmentli ilerleme çubuğunu oluşturur.
 * @param stepIndex Tamamlanan adım indeksi.
 * @param totalSteps Toplam adım sayısı.
 * @param isFailed İşlemin başarısız olup olmadığı.
 */
function StepProgress({
  stepIndex,
  totalSteps,
  isFailed,
}: {
  stepIndex: number;
  totalSteps: number;
  isFailed: boolean;
}) {
  const activeCount = Math.min(
    TOTAL_SEGMENTS,
    Math.round((stepIndex / Math.max(totalSteps, 1)) * TOTAL_SEGMENTS),
  );

  return (
    <div className="flex gap-1">
      {Array.from({ length: TOTAL_SEGMENTS }).map((_, index) => {
        const isCompleted = index < activeCount;
        let barColor = "bg-muted";

        if (isCompleted) {
          barColor = isFailed ? "bg-destructive" : "bg-emerald-600 dark:bg-emerald-500";
        }

        return (
          <div
            key={index}
            className={`h-1.5 w-4 rounded-full transition-colors ${barColor}`}
            data-testid="step-segment"
          />
        );
      })}
    </div>
  );
}

/**
 * Kaynak dosyalarının ilerleme durumunu ve hata metnini listeler.
 */
export default function SourceList({ items }: SourceListProps) {
  const { t } = useTranslation("admin");

  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">{t("sources.emptyList")}</div>
    );
  }

  return (
    <div className="space-y-3 pt-6">
      <div className="grid grid-cols-12 border-b border-border pb-2 text-xs font-semibold text-muted-foreground">
        <span className="col-span-5">{t("sources.table.file")}</span>
        <span className="col-span-4">{t("sources.table.status")}</span>
        <span className="col-span-3 text-right">{t("sources.table.result")}</span>
      </div>

      <div className="divide-y divide-border">
        {items.map((item) => {
          const isFailed = item.status === "FAILED";
          const isReview = item.status === "REVIEW";
          const isPublished = item.status === "PUBLISHED";
          const stepName = item.lastCompletedStep
            ? t(`sources.steps.${item.lastCompletedStep}`, { defaultValue: item.lastCompletedStep })
            : t(`sources.status.${item.status}`);

          return (
            <div key={item.sourceId} className="grid grid-cols-12 items-center py-4 text-sm">
              <div className="col-span-5 space-y-1 pr-4">
                <p className="font-medium text-foreground">{item.fileName}</p>
                <p className="text-xs text-muted-foreground">
                  {t(`sources.kinds.${item.kind}`, { defaultValue: item.kind })}
                </p>
                {item.error && (
                  <p role="alert" className="text-xs font-medium text-destructive">
                    {item.error}
                  </p>
                )}
              </div>

              <div className="col-span-4 space-y-1.5">
                <StepProgress
                  stepIndex={item.stepIndex}
                  totalSteps={item.totalSteps || TOTAL_SEGMENTS}
                  isFailed={isFailed}
                />
                <p className="text-xs text-muted-foreground">
                  {stepName} · {item.stepIndex}/{item.totalSteps || TOTAL_SEGMENTS}
                </p>
              </div>

              <div className="col-span-3 flex justify-end">
                {isPublished && (
                  <span className="inline-flex rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    {t("sources.status.PUBLISHED")}
                  </span>
                )}
                {isReview && (
                  <span className="inline-flex rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
                    {t("sources.status.REVIEW")}
                  </span>
                )}
                {isFailed && (
                  <span className="inline-flex rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs font-medium text-destructive">
                    {t("sources.status.FAILED")}
                  </span>
                )}
                {!isPublished && !isReview && !isFailed && (
                  <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                    {t(`sources.status.${item.status}`)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
