/**
 * Giriş ve kayıt sayfaları için marka panelli iki sütunlu düzeni sunar.
 */
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import Logo from "../../../components/Logo";
import { ROUTES } from "../../../lib/constants";

interface AuthLayoutProps {
  children: ReactNode;
}

/**
 * Solda lacivert marka panelini, sağda formu gösterir; dar ekranda yalnızca formu.
 * @param props Formun içeriği.
 * @returns Giriş ve kayıt düzeni.
 */
export default function AuthLayout({ children }: AuthLayoutProps) {
  const { t } = useTranslation("auth");

  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <aside className="hidden flex-col justify-between bg-navy p-12 text-white lg:flex">
        <Link to={ROUTES.landing} aria-label={t("brand.copyright")}>
          <Logo variant="lockupInverse" className="h-10 w-auto" />
        </Link>
        <div className="space-y-4">
          <h2 className="text-5xl font-semibold tracking-tight text-white">{t("brand.title")}</h2>
          <p className="text-lg text-white/75">{t("brand.description")}</p>
        </div>
        <p className="text-sm text-white/60">{t("brand.copyright")}</p>
      </aside>

      <div className="flex flex-col justify-center px-4 py-10 sm:px-8">
        <Link
          to={ROUTES.landing}
          aria-label={t("brand.copyright")}
          className="mx-auto mb-8 lg:hidden"
        >
          <Logo className="h-9 w-auto" />
        </Link>
        <div className="mx-auto w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
