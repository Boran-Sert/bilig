/**
 * Öğrencinin çözebileceği testleri listeler ve oturum başlatma bağlantısı sunar.
 */
import { useTranslation } from "react-i18next";
import { generatePath, useNavigate } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useTests } from "../../solve/api";
import TestCard from "../components/TestCard";
import TestFilters from "../components/TestFilters";
import TestSubjects from "../components/TestSubjects";

/**
 * Filtre alanlarını, ders kartlarını ve yayındaki testlerin kartlarını listeler.
 */
export default function TestListPage() {
  const { t } = useTranslation("test");
  const navigate = useNavigate();
  const { data: tests, isPending, isError, error } = useTests();

  /** Testi çözme sayfasına yönlendirir. */
  function handleStart(testId: number) {
    navigate(generatePath(ROUTES.solve, { testId: String(testId) }));
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

  const testCount = tests?.length ?? 0;

  return (
    <section className="space-y-8">
      <PageMeta title={t("testList.title")} description={t("testList.metaDescription")} />

      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{t("testList.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("testList.metaDescription")}</p>
      </div>

      <TestFilters />
      <TestSubjects totalCount={testCount} />

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-heading">{t("testList.sectionTitle")}</h2>
        <span className="text-sm text-muted-foreground">
          {t("testList.resultCount", { count: testCount })}
        </span>
      </div>

      {testCount === 0 && (
        <div className="py-12 text-center text-sm text-muted-foreground">{t("testList.empty")}</div>
      )}

      {tests && testCount > 0 && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => (
            <TestCard key={test.id} test={test} onStart={handleStart} />
          ))}
        </div>
      )}
    </section>
  );
}
