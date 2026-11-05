/**
 * Öğrencinin ilerleme özetini, başarısız kazanımlarını ve devam eden testlerini sunar.
 */
import { useTranslation } from "react-i18next";
import PageMeta from "../../../components/PageMeta";
import { useMe } from "../../auth/api";
import { useDashboard } from "../api";
import ActiveSessionsSection from "../components/ActiveSessionsSection";
import ErrorTypeDistributionSection from "../components/ErrorTypeDistributionSection";
import FailedOutcomesSection from "../components/FailedOutcomesSection";
import SummaryStats from "../components/SummaryStats";
import UnitAccuracySection from "../components/UnitAccuracySection";
import { getProblemMessage } from "../../../lib/api/problem";

/**
 * Öğrenci paneli ana görünümünü duyarlı yerleşimle çizer.
 */
export default function DashboardPage() {
  const { t } = useTranslation("dashboard");
  const { data: user } = useMe();
  const dashboardQuery = useDashboard();

  const data = dashboardQuery.data;

  return (
    <div className="space-y-6">
      <PageMeta title={t("title")} description={t("metaDescription")} />

      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          {t("greeting", { name: user?.displayName ?? "" })}
        </h1>
        <p className="text-xs text-muted-foreground sm:text-sm">
          {t("gradeAndCurriculum", { grade: user?.grade ?? 12 })}
        </p>
      </header>

      {dashboardQuery.isPending && (
        <p className="py-12 text-center text-sm text-muted-foreground">{t("loading")}</p>
      )}

      {dashboardQuery.isError && (
        <p role="alert" className="py-12 text-center text-sm text-destructive">
          {getProblemMessage(dashboardQuery.error)}
        </p>
      )}

      {data && (
        <div className="space-y-6">
          <SummaryStats summary={data.summary} />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="space-y-6">
              <ActiveSessionsSection sessions={data.activeSessions} />
              <FailedOutcomesSection outcomes={data.failedOutcomes} />
            </div>

            <div className="space-y-6">
              <UnitAccuracySection unitAccuracy={data.unitAccuracy} />
              <ErrorTypeDistributionSection errorTypeDistribution={data.errorTypeDistribution} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
