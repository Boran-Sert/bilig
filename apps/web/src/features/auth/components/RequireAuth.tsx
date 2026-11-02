/**
 * Girişsiz kullanıcıyı giriş sayfasına gönderen sarmalayıcı.
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useMe } from "../api";

interface RequireAuthProps {
  children: ReactNode;
}

/**
 * Oturum varsa içeriği, yoksa giriş sayfasına yönlendirmeyi gösterir.
 * @param props Bileşen özellikleri.
 * @returns Korumalı içerik, hata mesajı veya yönlendirme.
 */
export default function RequireAuth({ children }: RequireAuthProps) {
  const { data: user, isPending, isError, error } = useMe();
  const location = useLocation();

  if (isPending) {
    return null;
  }

  if (isError) {
    return (
      <p role="alert" className="py-10 text-center text-sm text-destructive">
        {getProblemMessage(error)}
      </p>
    );
  }

  if (!user) {
    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
