/**
 * Öğrenci paneli verilerini TanStack Query hook'larıyla sunar.
 */
import { useQuery } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import type { DashboardResponse } from "./types";

export const dashboardKeys = {
  me: ["dashboard", "me"] as const,
};

/**
 * Giriş yapmış öğrencinin panel istatistiklerini GET /api/me/dashboard ucundan çeker.
 */
export function useDashboard(enabled = true) {
  return useQuery<DashboardResponse, ApiError>({
    queryKey: dashboardKeys.me,
    enabled,
    /** Panel özetini sunucudan getirir. */
    queryFn: async (): Promise<DashboardResponse> => {
      const { data, error, response } = await client.GET("/api/me/dashboard");
      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}
