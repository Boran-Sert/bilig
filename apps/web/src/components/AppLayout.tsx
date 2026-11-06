/**
 * Uygulamanın ortak sayfa düzeni.
 * Üst başlığı ve yönlendirilen sayfanın içeriğini gösterir.
 */
import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useLogout, useMe } from "../features/auth/api";
import { getProblemMessage } from "../lib/api/problem";
import { ROUTES } from "../lib/constants";
import { cn } from "../lib/utils";
import Logo from "./Logo";
import { Button } from "./ui/button";

/** Üst başlıktaki bağlantının etkin ve pasif görünümünü belirler. */
function getNavLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-white/15 text-white" : "text-white/75 hover:bg-white/10 hover:text-white",
  );
}

/** Uygulamanın ortak üst başlığını ve sayfa içeriğini oluşturur. */
export default function AppLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const logout = useLogout();

  /** Oturumu kapatır; başarısızsa hata başlıkta görünür. */
  function handleLogout() {
    logout.mutate(undefined, {
      /** Kullanıcıyı giriş sayfasına gönderir. */
      onSuccess: () => navigate(ROUTES.login, { replace: true }),
    });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-navy text-white">
        <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-2 sm:px-6 lg:px-8">
          <Link to={ROUTES.home} aria-label={t("app.name")} className="shrink-0">
            <Logo variant="lockupInverse" className="h-9 w-auto" />
          </Link>

          {user && (
            <nav className="order-3 flex w-full items-center gap-1 sm:order-none sm:w-auto">
              <NavLink to={ROUTES.home} className={getNavLinkClass}>
                {t("navigation.dashboard")}
              </NavLink>
              <NavLink to={ROUTES.tests} className={getNavLinkClass}>
                {t("navigation.tests")}
              </NavLink>
              {user.canManageContent && (
                <>
                  <NavLink to={ROUTES.adminSources} className={getNavLinkClass}>
                    {t("navigation.adminSources")}
                  </NavLink>
                  <NavLink to={ROUTES.adminReview} className={getNavLinkClass}>
                    {t("navigation.adminReview")}
                  </NavLink>
                </>
              )}
            </nav>
          )}

          {user && (
            <div className="flex items-center gap-3">
              {logout.isError && (
                <p role="alert" className="text-sm text-white">
                  {getProblemMessage(logout.error)}
                </p>
              )}
              <Button
                variant="ghost"
                onClick={handleLogout}
                disabled={logout.isPending}
                className="border-white/30! text-white hover:bg-white/10! hover:text-white!"
              >
                {logout.isPending
                  ? t("logout.loading", { ns: "auth" })
                  : t("logout.button", { ns: "auth" })}
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
