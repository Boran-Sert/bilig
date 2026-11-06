/**
 * Karşılama başlığının yanında ürünün sonuç ekranını örnek veriyle gösterir.
 */
import { useTranslation } from "react-i18next";

const PREVIEW_BARS = [
  { key: "groupA", percent: 72 },
  { key: "groupB", percent: 55 },
] as const;

/**
 * Yanlış cevap kartını ve kazanım başarısı çubuklarını çizer.
 */
export default function LandingHeroPreview() {
  const { t } = useTranslation("landing");

  return (
    <div className="space-y-4">
      <div className="space-y-4 rounded-3xl border border-border bg-card p-6 shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-lg font-semibold text-heading">{t("hero.preview.question")}</span>
          <span className="rounded-full bg-danger-soft px-3 py-1 text-xs font-medium text-destructive">
            {t("hero.preview.wrongBadge")}
          </span>
        </div>
        <p className="text-foreground">{t("hero.preview.outcome")}</p>
        <div className="space-y-2 rounded-xl bg-teal-soft p-4">
          <p className="text-xs font-medium tracking-wider text-teal-strong">
            {t("hero.preview.citationLabel")}
          </p>
          <p className="text-heading">{t("hero.preview.citationText")}</p>
        </div>
        <span className="inline-flex h-10 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground">
          {t("hero.preview.similar")}
        </span>
      </div>

      <div className="space-y-3 rounded-2xl bg-navy p-6 text-white">
        <p className="text-sm text-white/70">{t("hero.preview.progressTitle")}</p>
        {PREVIEW_BARS.map((bar) => (
          <div key={bar.key} className="space-y-1">
            <p className="text-xs font-medium">{t(`hero.preview.${bar.key}`)}</p>
            <div className="h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-teal" style={{ width: `${bar.percent}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
