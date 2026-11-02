/**
 * useUploadSources hook'unun multipart istek yapısını ve hata davranışını test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import { useUploadSources } from "./api";

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}));

vi.mock("../../lib/api/client", () => ({
  client: { POST: postMock },
}));

/** Hook'u test sorgu istemcisiyle çalıştıran sarmalayıcıyı üretir. */
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

afterEach(cleanup);

describe("useUploadSources", () => {
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
    const [path, options] = postMock.mock.calls[0];
    expect(path).toBe("/api/admin/sources");

    // bodySerializer çağrılarak FormData oluşturulmasını test eder
    const serializedBody = options.bodySerializer(options.body) as FormData;
    expect(serializedBody).toBeInstanceOf(FormData);
    expect(serializedBody.getAll("files")).toHaveLength(1);
    expect(serializedBody.getAll("files")[0]).toBe(file);
    expect(result.current.data).toEqual(mockResponse);
  });

  test("birden fazla PDF dosyasını tek bir HTTP isteğinde gönderir", async () => {
    const mockResponse = {
      files: [
        { sourceId: 101, fileName: "ders-kitabi.pdf", duplicate: false },
        { sourceId: 102, fileName: "tekrar.pdf", duplicate: true },
      ],
    };
    postMock.mockResolvedValue({
      data: mockResponse,
      response: { status: 202 },
    });

    const { result } = renderHook(() => useUploadSources(), {
      wrapper: createWrapper(queryClient),
    });

    const file1 = new File(["pdf-1"], "ders-kitabi.pdf", { type: "application/pdf" });
    const file2 = new File(["pdf-2"], "tekrar.pdf", { type: "application/pdf" });

    result.current.mutate([file1, file2]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(postMock).toHaveBeenCalledTimes(1);
    const options = postMock.mock.calls[0][1];
    const serializedBody = options.bodySerializer(options.body) as FormData;
    const filesInFormData = serializedBody.getAll("files");

    expect(filesInFormData).toHaveLength(2);
    expect(filesInFormData[0]).toBe(file1);
    expect(filesInFormData[1]).toBe(file2);
    expect(result.current.data?.files?.[1].duplicate).toBe(true);
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
