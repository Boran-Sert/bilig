/**
 * Test listeleme, oturum başlatma ve cevap kaydı hook'larının API davranışını test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import { useStartSession, useSubmitAnswer, useTests } from "./api";

const { getMock, postMock, putMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  putMock: vi.fn(),
}));

vi.mock("../../lib/api/client", () => ({
  client: { GET: getMock, POST: postMock, PUT: putMock },
}));

/** Hook'u test sorgu istemcisiyle çalıştıran sarmalayıcıyı üretir. */
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

afterEach(cleanup);

describe("solve api", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    putMock.mockReset();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
  });

  test("useTests test listesini başarıyla çeker", async () => {
    const mockTests = [
      {
        id: 1,
        title: "Roman Testi",
        questionCount: 10,
        answeredCount: 0,
        sessionId: null,
        status: null,
      },
    ];
    getMock.mockResolvedValue({ data: mockTests, response: { status: 200 } });

    const { result } = renderHook(() => useTests(), { wrapper: createWrapper(queryClient) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getMock).toHaveBeenCalledWith("/api/tests");
    expect(result.current.data).toEqual(mockTests);
  });

  test("useStartSession oturum açar veya kaldığı yerden getirir", async () => {
    const mockSession = { sessionId: 99, currentPosition: 3, questions: [] };
    postMock.mockResolvedValue({ data: mockSession, response: { status: 200 } });

    const { result } = renderHook(() => useStartSession(), { wrapper: createWrapper(queryClient) });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(postMock).toHaveBeenCalledWith("/api/tests/{id}/sessions", {
      params: { path: { id: 1 } },
    });
    expect(result.current.data?.currentPosition).toBe(3);
  });

  test("useSubmitAnswer cevabı kaydeder ve doğru şık ile kazanımları döner", async () => {
    const mockAnswer = {
      isCorrect: false,
      correctOption: "B",
      outcomes: [{ code: "A.2.15", title: "Yazar ve eserler" }],
    };
    putMock.mockResolvedValue({ data: mockAnswer, response: { status: 200 } });

    const { result } = renderHook(() => useSubmitAnswer(), { wrapper: createWrapper(queryClient) });

    result.current.mutate({
      sessionId: 99,
      questionId: 5,
      request: { selectedOption: "A" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(putMock).toHaveBeenCalledWith("/api/sessions/{id}/answers/{questionId}", {
      params: { path: { id: 99, questionId: 5 } },
      body: { selectedOption: "A" },
    });
    expect(result.current.data?.isCorrect).toBe(false);
    expect(result.current.data?.correctOption).toBe("B");
    expect(result.current.data?.outcomes[0].code).toBe("A.2.15");
  });

  test("sunucu hatasında ApiError fırlatır", async () => {
    postMock.mockResolvedValue({
      error: { code: "SESSION_NOT_FOUND" },
      response: { status: 404 },
    });

    const { result } = renderHook(() => useStartSession(), { wrapper: createWrapper(queryClient) });

    result.current.mutate(999);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error?.status).toBe(404);
  });
});
