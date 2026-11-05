/**
 * Uygulamanın sayfa yönlendirmelerini tanımlar.
 */
import { createBrowserRouter, Link } from "react-router";
import { useTranslation } from "react-i18next";
import AppLayout from "./components/AppLayout";
import PageMeta from "./components/PageMeta";
import SourcesPage from "./features/admin/pages/SourcesPage";
import RedirectIfAuthenticated from "./features/auth/components/RedirectIfAuthenticated";
import RequireAuth from "./features/auth/components/RequireAuth";
import LoginPage from "./features/auth/pages/LoginPage";
import RegisterPage from "./features/auth/pages/RegisterPage";
import SolvePage from "./features/solve/pages/SolvePage";
import TestListPage from "./features/tests/pages/TestListPage";
import { ROUTES } from "./lib/constants";
import ResultPage from "./features/solve/pages/ResultPage";
import DashboardPage from "./features/dashboard/pages/DashboardPage";

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
            <DashboardPage />
          </RequireAuth>
        ),
      },
      {
        path: ROUTES.tests,
        element: (
          <RequireAuth>
            <TestListPage />
          </RequireAuth>
        ),
      },
      {
        path: ROUTES.solve,
        element: (
          <RequireAuth>
            <SolvePage />
          </RequireAuth>
        ),
      },
      {
        path: ROUTES.testResult,
        element: (
          <RequireAuth>
            <ResultPage />
          </RequireAuth>
        ),
      },
      {
        path: ROUTES.adminSources,
        element: (
          <RequireAuth>
            <SourcesPage />
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
