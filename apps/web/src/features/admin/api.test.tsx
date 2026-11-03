/**
 * Kaynak yükleme ve listeleme hook'larının istek yapısını ve yenileme davranışını test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import { SOURCES_POLL_INTERVAL_MS } from "../../lib/constants";
import { adminKeys, hasProcessingSources, useSources, useUploadSources } from "./api";
import type { SourceListItem } from "./types";

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("../../lib/api/client", () => ({
  client: { GET: getMock, POST: postMock },
}));

/** Hook'u test sorgu istemcisiyle çalıştıran sarmalayıcıyı üretir. */
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("admin api - hasProcessingSources", () => {
  test("UPLOADED veya PROCESSING durumunda true döndürür", () => {
    const items = [
      { status: "PUBLISHED" } as SourceListItem,
      { status: "PROCESSING" } as SourceListItem,
    ];
    expect(hasProcessingSources(items)).toBe(true);
  });

  test("tüm dosyalar tamamlandığında veya başarısız olduğunda false döndürür", () => {
    const items = [
      { status: "PUBLISHED" } as SourceListItem,
      { status: "FAILED" } as SourceListItem,
      { status: "REVIEW" } as SourceListItem,
    ];
    expect(hasProcessingSources(items)).toBe(false);
  });

  test("boş listede false döndürür", () => {
    expect(hasProcessingSources([])).toBe(false);
  });
});

describe("admin api - useSources", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    getMock.mockReset();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  /** Verilen durumdaki tek kaynakla liste yanıtını taklit eder. */
  function mockSourcesWithStatus(status: SourceListItem["status"]) {
    const item = { sourceId: 1, fileName: "kitap.pdf", status, stepIndex: 2, totalSteps: 6 };
    getMock.mockResolvedValue({
      data: { items: [item], page: 0, size: 20, total: 1 },
      response: { status: 200 },
    });
  }

  test("kaynak listesini sunucudan başarıyla çeker", async () => {
    mockSourcesWithStatus("PUBLISHED");

    const { result } = renderHook(() => useSources(true), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMock).toHaveBeenCalledWith("/api/admin/sources", {
      params: { query: { page: 0, size: 20 } },
    });
    expect(result.current.data?.items).toHaveLength(1);
  });

  test("yetki yokken listeyi istemez", () => {
    renderHook(() => useSources(false), { wrapper: createWrapper(queryClient) });

    expect(getMock).not.toHaveBeenCalled();
  });

  test("işlenen dosya varken 3 saniyede bir yeniden ister", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockSourcesWithStatus("PROCESSING");

    const { result } = renderHook(() => useSources(true), {
      wrapper: createWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    await vi.advanceTimersByTimeAsync(SOURCES_POLL_INTERVAL_MS);

    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
  });

  test("işlenen dosya yokken yenileme durur (Kabul Kriteri 1)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockSourcesWithStatus("PUBLISHED");

    const { result } = renderHook(() => useSources(true), {
      wrapper: createWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    await vi.advanceTimersByTimeAsync(SOURCES_POLL_INTERVAL_MS * 3);

    expect(getMock).toHaveBeenCalledTimes(1);
  });
});

describe("admin api - useUploadSources", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    postMock.mockReset();
    queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });
  });

  test("tek bir PDF dosyasını multipart form olarak sunucuya gönderir", async () => {
    const mockResponse = {
      files: [{ sourceId: 101, fileName: "test.pdf", duplicate: false }],
    };
    postMock.mockResolvedValue({
      data: mockResponse,
      response: { status: 202 },
    });

    const { result } = renderHook(() => useUploadSources(), {
      wrapper: createWrapper(queryClient),
    });

    const file = new File(["dummy pdf content"], "test.pdf", { type: "application/pdf" });
    result.current.mutate([file]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(postMock).toHaveBeenCalledTimes(1);
    const options = postMock.mock.calls[0][1];
    const serializedBody = options.bodySerializer(options.body) as FormData;
    expect(serializedBody).toBeInstanceOf(FormData);
    expect(serializedBody.getAll("files")).toHaveLength(1);
  });

  test("yükleme bitince kaynak listesini yeniler", async () => {
    postMock.mockResolvedValue({
      data: { files: [{ sourceId: 101, fileName: "test.pdf", duplicate: false }] },
      response: { status: 202 },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUploadSources(), {
      wrapper: createWrapper(queryClient),
    });
    result.current.mutate([new File(["içerik"], "test.pdf", { type: "application/pdf" })]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: adminKeys.sources });
  });

  test("sunucu RFC 9457 hata kodu döndüğünde ApiError fırlatır", async () => {
    postMock.mockResolvedValue({
      error: { code: "FILE_NOT_PDF" },
      response: { status: 400 },
    });

    const { result } = renderHook(() => useUploadSources(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate([new File(["bad content"], "not-pdf.txt", { type: "text/plain" })]);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error?.status).toBe(400);
    expect(result.current.error?.message).toBe("FILE_NOT_PDF");
  });
});
