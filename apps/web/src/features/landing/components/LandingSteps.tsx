/**
 * Karşılama sayfasında Bilig'in üç adımlık çalışma biçimini anlatır.
 */
import { useTranslation } from "react-i18next";

const STEPS = ["solve", "review", "practice"] as const;

/**
 * Numaralı adımları başlık ve açıklamayla yan yana dizer.
 */
export default function LandingSteps() {
  const { t } = useTranslation("landing");

  return (
    <section id="nasil-calisir" className="bg-info-soft py-20">
      <div className="mx-auto max-w-6xl space-y-12 px-4 sm:px-6">
        <div className="max-w-2xl space-y-3">
          <p className="text-xs font-medium tracking-wider text-teal-strong">
            {t("steps.overline")}
          </p>
          <h2 className="text-3xl font-semibold tracking-tight text-heading">{t("steps.title")}</h2>
        </div>

        <ol className="grid gap-8 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step} className="space-y-3">
              <span className="flex size-12 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground">
                {index + 1}
              </span>
              <h3 className="text-xl font-semibold text-heading">{t(`steps.${step}.title`)}</h3>
              <p className="text-foreground">{t(`steps.${step}.description`)}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
