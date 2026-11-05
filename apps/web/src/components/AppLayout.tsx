/**
 * Uygulamanın ortak sayfa düzeni.
 * Üst başlığı ve yönlendirilen sayfanın içeriğini gösterir.
 */
import { Link, Outlet, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useLogout, useMe } from "../features/auth/api";
import { getProblemMessage } from "../lib/api/problem";
import { ROUTES } from "../lib/constants";
import { Button } from "./ui/button";

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
      <header className="border-b border-border">
        <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-2 sm:px-6 sm:py-0 lg:px-8">
          <Link
            to={ROUTES.home}
            className="text-xl font-semibold tracking-tight"
            aria-label={t("app.name")}
          >
            {t("app.name")}
          </Link>

          {user && (
            <div className="flex items-center gap-3">
              {user.canManageContent && (
                <Link to={ROUTES.adminSources} className="text-sm font-medium hover:underline">
                  {t("navigation.adminSources")}
                </Link>
              )}
              {logout.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {getProblemMessage(logout.error)}
                </p>
              )}
              <Button variant="outline" onClick={handleLogout} disabled={logout.isPending}>
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
