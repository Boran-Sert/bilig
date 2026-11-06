/**
 * Test tamamlandığında öğrencinin net puanını ve kazanım bazlı özetini gösterir.
 */
import { useTranslation } from "react-i18next";
import { generatePath, Link, useParams } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { ROUTES } from "../../../lib/constants";
import { useSessionResult } from "../api";
import type { SessionCompletionOutcome } from "../types";

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
  const { sessionId } = useParams();
  const { data: result, isPending } = useSessionResult(Number(sessionId));

  if (isPending) {
    return <p className="py-12 text-center text-muted-foreground">{t("result.loading")}</p>;
  }

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

      <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
        <div className="rounded-2xl bg-navy p-5 text-white shadow-sm">
          <div className="text-3xl font-semibold">{formattedNet}</div>
          <div className="mt-1 text-xs font-medium text-white/70">{t("result.netScore")}</div>
        </div>
        <div className="rounded-2xl bg-success-soft p-5 shadow-sm">
          <div className="text-3xl font-semibold text-success">{result.correct}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">
            {t("result.correct")}
          </div>
        </div>
        <div className="rounded-2xl bg-danger-soft p-5 shadow-sm">
          <div className="text-3xl font-semibold text-destructive">{result.wrong}</div>
          <div className="mt-1 text-xs font-medium text-muted-foreground">{t("result.wrong")}</div>
        </div>
        <div className="rounded-2xl bg-navy-soft p-5 shadow-sm">
          <div className="text-3xl font-semibold text-muted-foreground">{result.blank}</div>
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
              className={`flex items-center justify-between rounded-xl border p-4 transition-colors ${
                outcome.failed
                  ? "border-destructive/40 bg-danger-soft shadow-sm"
                  : "border-border bg-card text-card-foreground"
              }`}
            >
              <div className="space-y-1 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{outcome.code}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      outcome.failed ? "bg-destructive text-white" : "bg-navy-soft text-navy"
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

      <div className="flex flex-col justify-center gap-3 pt-4 sm:flex-row">
        <Link to={ROUTES.tests}>
          <Button variant="outline" className="h-12 w-full rounded-xl px-7 text-base sm:w-auto">
            {t("result.backToTests")}
          </Button>
        </Link>
        <Link to={generatePath(ROUTES.sessionReview, { sessionId: String(sessionId) })}>
          <Button className="h-12 w-full rounded-xl px-7 text-base sm:w-auto">
            {t("result.reviewTest")}
          </Button>
        </Link>
      </div>
    </section>
  );
}
