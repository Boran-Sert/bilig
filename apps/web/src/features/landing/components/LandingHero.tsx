/**
 * Karşılama sayfasının başlık bölümünü ve ürün önizlemesini sunar.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { actionLinkClass, linkButtonClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";
import LandingHeroPreview from "./LandingHeroPreview";

/**
 * Başlığı, açıklamayı ve ana eylem düğmelerini yanında önizlemeyle gösterir.
 */
export default function LandingHero() {
  const { t } = useTranslation("landing");

  return (
    <section className="bg-linear-to-b from-info-soft to-background">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
        <div className="space-y-6">
          <h1 className="text-4xl font-semibold tracking-tight text-heading sm:text-5xl">
            {t("hero.title")}
          </h1>
          <p className="text-lg text-foreground">{t("hero.description")}</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link to={ROUTES.register} className={actionLinkClass("h-12! px-7! text-base")}>
              {t("hero.primaryCta")}
            </Link>
            <a href="#nasil-calisir" className={linkButtonClass("outline", "h-12 px-7 text-base")}>
              {t("hero.secondaryCta")}
            </a>
          </div>
        </div>
        <LandingHeroPreview />
      </div>
    </section>
  );
}
