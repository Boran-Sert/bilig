/**
 * Uygulamanın sayfa yönlendirmelerini tanımlar.
 */
import { createBrowserRouter, Link } from "react-router";
import { useTranslation } from "react-i18next";
import AppLayout from "./components/AppLayout";
import PageMeta from "./components/PageMeta";
import RedirectIfAuthenticated from "./features/auth/components/RedirectIfAuthenticated";
import RequireAuth from "./features/auth/components/RequireAuth";
import LoginPage from "./features/auth/pages/LoginPage";
import RegisterPage from "./features/auth/pages/RegisterPage";
import { ROUTES } from "./lib/constants";

/** Ana sayfayı gösterir. */
function HomePage() {
  const { t } = useTranslation();

  return (
    <section className="space-y-3">
      <PageMeta title={t("home.title")} description={t("home.metaDescription")} />
      <h1 className="text-2xl font-semibold tracking-tight">{t("app.name")}</h1>
      <p className="max-w-2xl text-muted-foreground">{t("app.description")}</p>
    </section>
  );
}

/** Bulunamayan sayfa görünümünü gösterir. */
function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <section className="space-y-4 py-8">
      <PageMeta title={t("notFound.title")} description={t("notFound.description")} />
      <h1 className="text-2xl font-semibold">{t("notFound.title")}</h1>
      <p className="text-muted-foreground">{t("notFound.description")}</p>
      <Link to={ROUTES.home} className="inline-flex underline underline-offset-4">
        {t("notFound.backHome")}
      </Link>
    </section>
  );
}

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: ROUTES.home,
        element: (
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        ),
      },
      {
        path: ROUTES.login,
        element: (
          <RedirectIfAuthenticated>
            <LoginPage />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: ROUTES.register,
        element: (
          <RedirectIfAuthenticated>
            <RegisterPage />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
]);
