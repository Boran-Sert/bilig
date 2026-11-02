/**
 * Giriş yapmış kullanıcıyı giriş ve kayıt sayfalarından uzaklaştırır.
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useMe } from "../api";
import { getReturnPath } from "../returnPath";

interface RedirectIfAuthenticatedProps {
  children: ReactNode;
}

/**
 * Oturum yoksa içeriği, varsa dönüş sayfasına yönlendirmeyi gösterir.
 * @param props Bileşen özellikleri.
 * @returns Misafir içeriği veya yönlendirme.
 */
export default function RedirectIfAuthenticated({ children }: RedirectIfAuthenticatedProps) {
  const { data: user, isPending } = useMe();
  const location = useLocation();

  if (isPending) {
    return null;
  }

  if (user) {
    return <Navigate to={getReturnPath(location.state)} replace />;
  }

  return <>{children}</>;
}
