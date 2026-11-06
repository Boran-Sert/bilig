/**
 * Karşılama sayfasında kurumlara özel entegrasyon teklifini sunar.
 */
import { useTranslation } from "react-i18next";
import ActionButton from "../../../components/ActionButton";

const ITEMS = ["integration", "data", "support"] as const;

/**
 * Lacivert zeminde kurum başlığını, maddeleri ve iletişim düğmesini gösterir.
 */
export default function LandingInstitutions() {
  const { t } = useTranslation("landing");

  return (
    <section id="kurumlar" className="bg-navy py-20 text-white">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
        <div className="space-y-5">
          <p className="text-xs font-medium tracking-wider text-teal">
            {t("institutions.overline")}
          </p>
          <h2 className="text-3xl font-semibold tracking-tight text-white">
            {t("institutions.title")}
          </h2>
          <p className="text-lg text-white/75">{t("institutions.description")}</p>
          <ActionButton className="h-12! px-7! text-base">{t("institutions.cta")}</ActionButton>
        </div>

        <ul className="space-y-3">
          {ITEMS.map((item) => (
            <li
              key={item}
              className="rounded-2xl border border-white/10 bg-white/10 px-6 py-4 text-lg font-medium"
            >
              {t(`institutions.items.${item}`)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
