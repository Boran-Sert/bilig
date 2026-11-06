/**
 * Ünite ve edebi tür bazlı başarı oranlarını ilerleme çubuklarıyla gösterir.
 */
import { useTranslation } from "react-i18next";
import type { DashboardUnitAccuracy } from "../types";

interface UnitAccuracySectionProps {
  unitAccuracy: DashboardUnitAccuracy[];
}

/**
 * Her ünitenin başarı yüzdesini çubuk grafik şeklinde çizer.
 */
export default function UnitAccuracySection({ unitAccuracy }: UnitAccuracySectionProps) {
  const { t } = useTranslation("dashboard");

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-heading">{t("unitAccuracy.title")}</h2>

      {unitAccuracy.length === 0 ? (
        <p className="py-4 text-xs text-muted-foreground">{t("unitAccuracy.empty")}</p>
      ) : (
        <div className="space-y-3">
          {unitAccuracy.map((unit) => {
            const percent = Math.min(100, Math.max(0, Math.round(unit.accuracyPercent)));
            return (
              <div key={unit.unitTitle} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-heading">{unit.unitTitle}</span>
                  <span className="font-semibold text-muted-foreground">%{percent}</span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-navy-soft">
                  <div
                    className="h-full rounded-full bg-teal transition-all duration-300"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
