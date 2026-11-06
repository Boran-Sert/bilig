/**
 * Karşılama sayfasında öğrencilere sunulan üç ana özelliği gösterir.
 */
import { BookOpen, ChartColumn, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

const FEATURES = [
  { key: "analysis", icon: ChartColumn, tone: "bg-teal" },
  { key: "citation", icon: BookOpen, tone: "bg-info" },
  { key: "similar", icon: Sparkles, tone: "bg-action" },
] as const;

/**
 * Özellik kartlarını başlık ve açıklamasıyla çizer.
 */
export default function LandingStudents() {
  const { t } = useTranslation("landing");

  return (
    <section id="ogrenciler" className="bg-card py-20">
      <div className="mx-auto max-w-6xl space-y-12 px-4 sm:px-6">
        <div className="max-w-2xl space-y-3">
          <p className="text-xs font-medium tracking-wider text-teal-strong">
            {t("students.overline")}
          </p>
          <h2 className="text-3xl font-semibold tracking-tight text-heading">
            {t("students.title")}
          </h2>
          <p className="text-lg text-foreground">{t("students.description")}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {FEATURES.map(({ key, icon: Icon, tone }) => (
            <article key={key} className="space-y-4 rounded-2xl bg-navy-soft p-8">
              <span
                className={`flex size-12 items-center justify-center rounded-xl text-white ${tone}`}
              >
                <Icon className="size-6" aria-hidden="true" />
              </span>
              <h3 className="text-xl font-semibold text-heading">
                {t(`students.features.${key}.title`)}
              </h3>
              <p className="text-foreground">{t(`students.features.${key}.description`)}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
