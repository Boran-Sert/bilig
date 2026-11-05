/**
 * Dashboard hook'unun veri çekme ve hata yönetimini test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import { useDashboard } from "./api";
import type { DashboardResponse } from "./types";

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
}));

vi.mock("../../lib/api/client", () => ({
  client: { GET: getMock },
}));

/** Hook'u sorgu istemcisiyle çalıştıran sarmalayıcı. */
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

afterEach(cleanup);

describe("dashboard api - useDashboard", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    getMock.mockReset();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  test("öğrenci panelini başarıyla sunucudan çeker", async () => {
    const mockData: DashboardResponse = {
      summary: {
        answeredQuestionCount: 312,
        accuracyPercent: 64,
        latestNet: 15.25,
        latestQuestionCount: 24,
      },
      activeSessions: [],
      failedOutcomes: [],
      unitAccuracy: [],
      errorTypeDistribution: [],
    };
    getMock.mockResolvedValue({ data: mockData, response: { status: 200 } });

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getMock).toHaveBeenCalledWith("/api/me/dashboard");
    expect(result.current.data?.summary.answeredQuestionCount).toBe(312);
  });

  test("sunucu hatasında ApiError fırlatır", async () => {
    getMock.mockResolvedValue({
      error: { code: "UNAUTHORIZED" },
      response: { status: 401 },
    });

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error?.status).toBe(401);
  });
});
