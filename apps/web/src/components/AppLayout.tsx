/**
 * Uygulamanın ortak sayfa düzeni.
 * Üst başlığı ve yönlendirilen sayfanın içeriğini gösterir.
 */
import { Link, Outlet } from "react-router";
import { useTranslation } from "react-i18next";

/** Uygulamanın ortak üst başlığını ve sayfa içeriğini oluşturur. */
export default function AppLayout() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
          <Link to="/" className="text-xl font-semibold tracking-tight" aria-label={t("app.name")}>
            {t("app.name")}
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
