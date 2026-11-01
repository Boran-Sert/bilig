/**
 * Uygulamanın sayfa yönlendirmelerini tanımlar.
 */
import { createBrowserRouter, Link } from "react-router";
import { useTranslation } from "react-i18next";
import AppLayout from "./components/AppLayout";
import RequireAuth from "./features/auth/components/RequireAuth";
import LoginPage from "./features/auth/pages/LoginPage";
import RegisterPage from "./features/auth/pages/RegisterPage";

/** Ana sayfayı gösterir. */
function HomePage() {
  const { t } = useTranslation();

  return (
    <section className="space-y-3">
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
      <h1 className="text-2xl font-semibold">{t("notFound.title")}</h1>
      <p className="text-muted-foreground">{t("notFound.description")}</p>
      <Link to="/" className="inline-flex underline underline-offset-4">
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
        path: "/",
        element: (
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        ),
      },
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
]);
