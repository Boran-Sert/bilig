/**
 * Kazanım testlerinin hangi derslere ait olduğunu gösteren ders kartlarını sunar.
 * Ders verisi API'de olmadığı için yalnızca "Tümü" kartı gerçek sayıyı gösterir.
 */
import { ImageIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

interface TestSubjectsProps {
  totalCount: number;
}

const SUBJECT_KEYS = ["first", "second", "third", "fourth"] as const;

/**
 * Seçili "Tümü" kartını ve yakında gelecek ders kartlarını yan yana çizer.
 * @param props Toplam test sayısı.
 * @returns Ders kartları bölümü.
 */
export default function TestSubjects({ totalCount }: TestSubjectsProps) {
  const { t } = useTranslation("test");

  return (
    <section className="space-y-3" aria-labelledby="test-subjects-title">
      <h2 id="test-subjects-title" className="text-xl font-semibold text-heading">
        {t("testList.subjects.title")}
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <li className="flex items-center gap-3 rounded-xl bg-navy px-4 py-3 text-white">
          <span className="flex size-10 items-center justify-center rounded-lg bg-white/15">
            <ImageIcon className="size-5" aria-hidden="true" />
          </span>
          <span>
            <span className="block text-sm font-semibold">{t("testList.subjects.all")}</span>
            <span className="block text-sm text-white/70">
              {t("testList.subjects.testCount", { count: totalCount })}
            </span>
          </span>
        </li>
        {SUBJECT_KEYS.map((key) => (
          <li
            key={key}
            aria-disabled="true"
            className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 opacity-80"
          >
            <span className="flex size-10 items-center justify-center rounded-lg bg-navy-soft text-navy-strong/50">
              <ImageIcon className="size-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-semibold text-heading">
                {t(`testList.subjects.${key}`)}
              </span>
              <span className="block text-sm text-muted-foreground">
                {t("testList.subjects.comingSoon")}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
