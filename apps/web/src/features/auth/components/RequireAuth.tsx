/**
 * Oturumu denetler.
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useMe } from "../api";

interface RequireAuthProps {
  children: ReactNode;
}

/**
 * Yetkili içeriği gösterir.
 * @param props Bileşen özellikleri.
 * @returns Yetkili içerik veya yönlendirme.
 */
export default function RequireAuth({ children }: RequireAuthProps) {
  const { data: user, isPending, isError } = useMe();
  const location = useLocation();

  if (isPending) {
    return null;
  }

  if (isError || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
