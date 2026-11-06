/**
 * Öğrencinin yanlış cevaplarında yapay zeka tarafından tespit edilen hata türlerinin dağılımını gösterir.
 */
import { useTranslation } from "react-i18next";
import type { DashboardErrorTypeCount } from "../types";

interface ErrorTypeDistributionSectionProps {
  errorTypeDistribution: DashboardErrorTypeCount[];
}

const ERROR_TONES: Record<string, string> = {
  KNOWLEDGE: "bg-navy-soft text-navy",
  MISCONCEPTION: "bg-info-soft text-info-strong",
  ATTENTION: "bg-teal-soft text-teal-strong",
  READING: "bg-action/15 text-action-foreground",
};

/**
 * Hata türü yüzdelerini etiket ve sayaç olarak listeler.
 */
export default function ErrorTypeDistributionSection({
  errorTypeDistribution,
}: ErrorTypeDistributionSectionProps) {
  const { t } = useTranslation("dashboard");

  const totalErrors = errorTypeDistribution.reduce((sum, item) => sum + item.answerCount, 0);

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-heading">{t("errorTypes.title")}</h2>

      {totalErrors === 0 ? (
        <p className="py-4 text-xs text-muted-foreground">{t("errorTypes.empty")}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {errorTypeDistribution.map((item) => {
            const percent = Math.round((item.answerCount / totalErrors) * 100);
            const label = t(`errorTypes.${item.errorType}`, { defaultValue: item.errorType });

            return (
              <div
                key={item.errorType}
                className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${ERROR_TONES[item.errorType] ?? "bg-navy-soft text-navy"}`}
              >
                <span>{label}</span>
                <span className="font-semibold">%{percent}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
