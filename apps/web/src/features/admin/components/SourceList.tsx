/**
 * Kaynak dosyalarının durumunu ve hazırlık adımlarındaki ilerlemesini tablo olarak gösterir.
 */
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import type { SourceListItem } from "../types";
import StepProgress from "./StepProgress";

interface SourceListProps {
  items: SourceListItem[];
  answerKeys: SourceListItem[];
  isReprocessing: boolean;
  onReprocess: (sourceId: number, answerKeySourceId?: number) => void;
}

/**
 * Kaynak dosyalarının ilerleme durumunu, hata metnini ve yeniden işleme düğmelerini listeler.
 */
export default function SourceList({
  items,
  answerKeys,
  isReprocessing,
  onReprocess,
}: SourceListProps) {
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
          const isWorking = item.status === "UPLOADED" || item.status === "PROCESSING";
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
                  totalSteps={item.totalSteps}
                  isFailed={isFailed}
                />
                <p className="text-xs text-muted-foreground">
                  {stepName} · {item.stepIndex}/{item.totalSteps}
                </p>
              </div>

              <div className="col-span-3 flex flex-col items-end gap-2">
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
                {!isWorking && item.kind === "TEST" && answerKeys.length > 0 && (
                  <select
                    aria-label={t("sources.linkAnswerKey")}
                    value=""
                    disabled={isReprocessing}
                    onChange={(event) => onReprocess(item.sourceId, Number(event.target.value))}
                    className="h-7 max-w-full rounded-md border border-input bg-transparent px-2 text-xs"
                  >
                    <option value="" disabled>
                      {t("sources.linkAnswerKey")}
                    </option>
                    {answerKeys.map((answerKey) => (
                      <option key={answerKey.sourceId} value={answerKey.sourceId}>
                        {answerKey.fileName}
                      </option>
                    ))}
                  </select>
                )}
                {!isWorking && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isReprocessing}
                    onClick={() => onReprocess(item.sourceId)}
                  >
                    {t("sources.reprocess")}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
