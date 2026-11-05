/**
 * Öğrencinin test veya genel toplamda başarısız sayıldığı kazanımları listeler.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { buttonVariants } from "../../../components/ui/button";
import { ROUTES } from "../../../lib/constants";
import { cn } from "../../../lib/utils";
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
    <section className="space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">{t("failedOutcomes.title")}</h2>

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
                className="flex flex-col gap-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-foreground">{outcome.code}</span>
                    <span className="text-xs text-muted-foreground">{outcome.title}</span>
                  </div>
                  <p className="text-xs font-medium text-destructive">{detailText}</p>
                </div>
                <Link
                  to={ROUTES.tests}
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "w-full sm:w-auto",
                  )}
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
