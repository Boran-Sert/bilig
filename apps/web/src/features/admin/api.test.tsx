/**
 * Kaynak yükleme ve listeleme hook'larının istek yapısını ve yenileme davranışını test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import {
  hasProcessingSources,
  SOURCES_POLL_INTERVAL_MS,
  useSources,
  useUploadSources,
} from "./api";
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

afterEach(cleanup);

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

  test("kaynak listesini sunucudan başarıyla çeker", async () => {
    const mockPage = {
      items: [
        { sourceId: 1, fileName: "kitap.pdf", status: "PUBLISHED", stepIndex: 8, totalSteps: 8 },
      ],
      page: 0,
      size: 20,
      total: 1,
    };
    getMock.mockResolvedValue({
      data: mockPage,
      response: { status: 200 },
    });

    const { result } = renderHook(() => useSources(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMock).toHaveBeenCalledWith("/api/admin/sources", {
      params: { query: { page: 0, size: 20 } },
    });
    expect(result.current.data).toEqual(mockPage);
  });

  test("işlenen dosya yokken yenileme durur (hasProcessingSources false)", async () => {
    const mockPage = {
      items: [
        { sourceId: 1, fileName: "kitap.pdf", status: "PUBLISHED", stepIndex: 8, totalSteps: 8 },
      ],
      page: 0,
      size: 20,
      total: 1,
    };
    getMock.mockResolvedValue({
      data: mockPage,
      response: { status: 200 },
    });

    const { result } = renderHook(() => useSources(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(hasProcessingSources(result.current.data?.items)).toBe(false);
  });

  test("işlenen dosya varken 3 saniye (3000 ms) yenileme aralığı döner", () => {
    const processingItems = [
      { sourceId: 1, fileName: "isleniyor.pdf", status: "PROCESSING", stepIndex: 3, totalSteps: 8 },
    ] as SourceListItem[];

    expect(hasProcessingSources(processingItems)).toBe(true);
    expect(SOURCES_POLL_INTERVAL_MS).toBe(3000);
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
