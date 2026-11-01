/**
 * Uygulamanın ortak sayfa düzeni.
 * Üst başlığı ve yönlendirilen sayfanın içeriğini gösterir.
 */
import { Link, Outlet, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useLogout, useMe } from "../features/auth/api";

/** Uygulamanın ortak üst başlığını ve sayfa içeriğini oluşturur. */
export default function AppLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const logout = useLogout();

  /** Kullanıcı oturumunu kapatır ve giriş sayfasına yönlendirir. */
  async function handleLogout() {
    try {
      await logout.mutateAsync();
      navigate("/login", { replace: true });
    } catch {
      // Çıkış başarısızsa mevcut sayfada kal.
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="text-xl font-semibold tracking-tight" aria-label={t("app.name")}>
            {t("app.name")}
          </Link>

          {user && (
            <button
              type="button"
              onClick={handleLogout}
              disabled={logout.isPending}
              className="rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              {logout.isPending
                ? t("logout.loading", { ns: "auth" })
                : t("logout.button", { ns: "auth" })}
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
