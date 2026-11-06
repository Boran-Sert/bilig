/**
 * Karşılama sayfasının sonunda kayıt ve giriş çağrısını gösterir.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { actionLinkClass, linkButtonClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";

/**
 * Ortalanmış başlığı ve iki eylem düğmesini gösterir.
 */
export default function LandingCta() {
  const { t } = useTranslation("landing");

  return (
    <section className="bg-teal-soft py-16">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 text-center sm:px-6">
        <h2 className="text-3xl font-semibold tracking-tight text-heading sm:text-4xl">
          {t("cta.title")}
        </h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link to={ROUTES.register} className={actionLinkClass("h-12! px-7! text-base")}>
            {t("cta.primary")}
          </Link>
          <Link to={ROUTES.login} className={linkButtonClass("outline", "h-12 px-7 text-base")}>
            {t("cta.secondary")}
          </Link>
        </div>
      </div>
    </section>
  );
}
