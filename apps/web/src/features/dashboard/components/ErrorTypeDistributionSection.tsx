/**
 * Öğrencinin yanlış cevaplarında yapay zeka tarafından tespit edilen hata türlerinin dağılımını gösterir.
 */
import { useTranslation } from "react-i18next";
import type { DashboardErrorTypeCount } from "../types";

interface ErrorTypeDistributionSectionProps {
  errorTypeDistribution: DashboardErrorTypeCount[];
}

/**
 * Hata türü yüzdelerini etiket ve sayaç olarak listeler.
 */
export default function ErrorTypeDistributionSection({
  errorTypeDistribution,
}: ErrorTypeDistributionSectionProps) {
  const { t } = useTranslation("dashboard");

  const totalErrors = errorTypeDistribution.reduce((sum, item) => sum + item.answerCount, 0);

  return (
    <section className="space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">{t("errorTypes.title")}</h2>

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
                className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs"
              >
                <span className="text-muted-foreground">{label}</span>
                <span className="font-bold text-foreground">%{percent}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
