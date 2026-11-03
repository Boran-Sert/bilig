/**
 * Test tamamlandığında öğrencinin net puanını ve kazanım bazlı özetini gösterir.
 */
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { ROUTES } from "../../../lib/constants";
import type { SessionCompletionOutcome, SessionCompletionResponse } from "../types";

/**
 * Başarısız kazanımları en üste, ardından yanlış sayısına göre sıralar.
 */
function sortOutcomes(outcomes: SessionCompletionOutcome[]): SessionCompletionOutcome[] {
  return [...outcomes].sort((a, b) => {
    if (a.failed !== b.failed) {
      return a.failed ? -1 : 1;
    }
    return b.wrong - a.wrong;
  });
}

/**
 * Net puanını, soru sayılarını ve kazanım analizini sunar.
 */
export default function ResultPage() {
  const { t } = useTranslation("test");
  const location = useLocation();
  const result = (location.state as { result?: SessionCompletionResponse } | undefined)?.result;

  if (!result) {
    return (
      <section className="mx-auto max-w-xl py-12 text-center space-y-4">
        <PageMeta title={t("result.title")} description={t("result.metaDescription")} />
        <p className="text-muted-foreground">{t("result.noResultFound")}</p>
        <Link to={ROUTES.tests}>
          <Button variant="outline">{t("result.backToTests")}</Button>
        </Link>
      </section>
    );
  }

  const sortedOutcomes = sortOutcomes(result.outcomes);
  const formattedNet = result.net.toLocaleString("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <section className="mx-auto max-w-2xl space-y-8 py-6">
      <PageMeta title={t("result.title")} description={t("result.metaDescription")} />

      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("result.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("result.metaDescription")}</p>
      </div>

      <div className="grid grid-cols-4 gap-3 text-center">
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="text-3xl font-extrabold text-primary">{formattedNet}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">
            {t("result.netScore")}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="text-3xl font-extrabold text-emerald-600">{result.correct}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">
            {t("result.correct")}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="text-3xl font-extrabold text-rose-600">{result.wrong}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">{t("result.wrong")}</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="text-3xl font-extrabold text-muted-foreground">{result.blank}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">{t("result.blank")}</div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">{t("result.outcomesTitle")}</h2>
        <ul className="space-y-3" role="list">
          {sortedOutcomes.map((outcome) => (
            <li
              key={outcome.code}
              data-testid={`outcome-${outcome.code}`}
              className={`flex items-center justify-between rounded-lg border p-4 transition-colors ${
                outcome.failed
                  ? "border-destructive/50 bg-destructive/10 text-destructive-foreground shadow-sm"
                  : "border-border bg-card text-card-foreground"
              }`}
            >
              <div className="space-y-1 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{outcome.code}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      outcome.failed
                        ? "bg-destructive text-destructive-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {outcome.failed ? t("result.failedBadge") : t("result.successBadge")}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{outcome.title}</p>
              </div>

              <span className="shrink-0 text-xs font-medium text-muted-foreground">
                {t("result.wrongCount", { count: outcome.wrong })}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex justify-center pt-4">
        <Link to={ROUTES.tests}>
          <Button size="lg">{t("result.backToTests")}</Button>
        </Link>
      </div>
    </section>
  );
}
