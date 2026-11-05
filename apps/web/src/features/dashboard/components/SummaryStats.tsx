/**
 * Öğrencinin çözdüğü toplam soru, doğruluk oranı ve son deneme netini kartlarla gösterir.
 */
import { useTranslation } from "react-i18next";
import type { DashboardSummary } from "../types";

interface SummaryStatsProps {
  summary: DashboardSummary;
}

/**
 * Üç temel başarı metriğini özet kartlar halinde sunar.
 */
export default function SummaryStats({ summary }: SummaryStatsProps) {
  const { t } = useTranslation("dashboard");

  const formattedAccuracy = `%${Math.round(summary.accuracyPercent)}`;
  const hasLatestNet = summary.latestNet !== null && summary.latestQuestionCount !== null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <p className="text-3xl font-bold tracking-tight text-foreground">
          {summary.answeredQuestionCount}
        </p>
        <p className="text-xs text-muted-foreground">{t("summary.solvedQuestions")}</p>
      </div>

      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <p className="text-3xl font-bold tracking-tight text-foreground">{formattedAccuracy}</p>
        <p className="text-xs text-muted-foreground">{t("summary.accuracy")}</p>
      </div>

      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <p className="text-3xl font-bold tracking-tight text-foreground">
          {hasLatestNet ? summary.latestNet : "-"}
        </p>
        <p className="text-xs text-muted-foreground">
          {hasLatestNet
            ? t("summary.latestNet", { count: summary.latestQuestionCount })
            : t("summary.noNetYet")}
        </p>
      </div>
    </div>
  );
}
