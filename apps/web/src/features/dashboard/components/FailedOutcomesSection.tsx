/**
 * Öğrencinin test veya genel toplamda başarısız sayıldığı kazanımları listeler.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { linkButtonClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";
import type { DashboardFailedOutcome } from "../types";

interface FailedOutcomesSectionProps {
  outcomes: DashboardFailedOutcome[];
}

/**
 * Başarısız kazanımları ve pratik yap aksiyonunu sunar.
 */
export default function FailedOutcomesSection({ outcomes }: FailedOutcomesSectionProps) {
  const { t } = useTranslation("dashboard");

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-heading">{t("failedOutcomes.title")}</h2>

      {outcomes.length === 0 ? (
        <p className="py-4 text-xs text-muted-foreground">{t("failedOutcomes.empty")}</p>
      ) : (
        <div className="space-y-2">
          {outcomes.map((outcome, idx) => {
            const hasTestDetail = outcome.testTitle !== null && outcome.testWrongCount !== null;
            const detailText = hasTestDetail
              ? t("failedOutcomes.testWrong", {
                  test: outcome.testTitle,
                  count: outcome.testWrongCount,
                })
              : t("failedOutcomes.totalWrong", { count: outcome.totalWrongCount });

            return (
              <div
                key={idx}
                className="flex flex-col gap-2 rounded-xl bg-danger-soft p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-heading">{outcome.code}</span>
                    <span className="text-xs text-muted-foreground">{outcome.title}</span>
                  </div>
                  <p className="text-xs font-medium text-destructive">{detailText}</p>
                </div>
                <Link
                  to={ROUTES.tests}
                  className={linkButtonClass("outline", "w-full bg-card sm:w-auto")}
                >
                  {t("failedOutcomes.practice")}
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
