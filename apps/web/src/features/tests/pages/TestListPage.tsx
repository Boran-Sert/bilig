/**
 * Öğrencinin çözebileceği testleri listeler ve oturum başlatma bağlantısı sunar.
 */
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { useTests } from "../../solve/api";

/**
 * Yayındaki testlerin kartlarını ve ilerleme durumlarını listeler.
 */
export default function TestListPage() {
  const { t } = useTranslation("test");
  const navigate = useNavigate();
  const { data: tests, isPending, isError, error } = useTests();

  /** Testi çözme sayfasına yönlendirir. */
  function handleStart(testId: number) {
    navigate(`/tests/${testId}/solve`);
  }

  if (isPending) {
    return null;
  }

  if (isError) {
    return (
      <p role="alert" className="py-12 text-center text-sm font-medium text-destructive">
        {getProblemMessage(error)}
      </p>
    );
  }

  return (
    <section className="space-y-6">
      <PageMeta title={t("testList.title")} description={t("testList.metaDescription")} />

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("testList.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("testList.metaDescription")}</p>
      </div>

      {(!tests || tests.length === 0) && (
        <div className="py-12 text-center text-sm text-muted-foreground">{t("testList.empty")}</div>
      )}

      {tests && tests.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => {
            const hasProgress = (test.answeredCount ?? 0) > 0 || test.sessionId !== null;
            const isCompleted = test.status === "COMPLETED";

            return (
              <div
                key={test.id}
                className="flex flex-col justify-between rounded-lg border border-border p-5 transition-shadow hover:shadow-sm"
              >
                <div className="space-y-2">
                  <h2 className="text-base font-semibold text-foreground">{test.title}</h2>
                  <p className="text-xs text-muted-foreground">
                    {hasProgress
                      ? t("testList.answeredCount", {
                          count: test.answeredCount,
                          total: test.questionCount,
                        })
                      : t("testList.questionCount", { count: test.questionCount })}
                  </p>
                </div>

                <div className="mt-6 flex items-center justify-between">
                  {isCompleted ? (
                    <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      {t("testList.completed")}
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant={hasProgress ? "default" : "outline"}
                      onClick={() => handleStart(test.id)}
                    >
                      {hasProgress ? t("testList.resume") : t("testList.start")}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
