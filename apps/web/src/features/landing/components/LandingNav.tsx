/**
 * Karşılama sayfasının üst gezinme çubuğunu sunar.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import Logo from "../../../components/Logo";
import { linkButtonClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";

/**
 * Logoyu, bölüm bağlantılarını ve giriş düğmelerini gösterir.
 */
export default function LandingNav() {
  const { t } = useTranslation("landing");

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-card/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to={ROUTES.landing} aria-label={t("meta.title")}>
          <Logo className="h-9 w-auto" />
        </Link>

        <nav className="hidden items-center gap-8 text-sm font-medium text-foreground md:flex">
          <a href="#ogrenciler" className="hover:text-heading">
            {t("nav.students")}
          </a>
          <a href="#nasil-calisir" className="hover:text-heading">
            {t("nav.howItWorks")}
          </a>
          <a href="#kurumlar" className="hover:text-heading">
            {t("nav.institutions")}
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to={ROUTES.login}
            className={linkButtonClass("ghost", "text-info hover:text-info-strong")}
          >
            {t("nav.login")}
          </Link>
          <Link to={ROUTES.register} className={linkButtonClass("default")}>
            {t("nav.start")}
          </Link>
        </div>
      </div>
    </header>
  );
}
