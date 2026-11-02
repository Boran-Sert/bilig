/**
 * Kimlik doğrulama hook'larının oturum ve önbellek davranışını test eder.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../../lib/api/problem";
import { authKeys, clearSessionOnUnauthorized, useLogin, useLogout, useMe } from "./api";

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("../../lib/api/client", () => ({
  client: { GET: getMock, POST: postMock },
}));

const user = {
  id: 1,
  email: "ogrenci@example.test",
  displayName: "Ogrenci",
  role: "STUDENT",
  grade: 12,
  explainStyle: "SIMPLE",
};

/** Önceki kullanıcıya ait veri bulunan sorgu istemcisi oluşturur. */
function createQueryClientWithPreviousUser() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  queryClient.setQueryData(authKeys.me, { ...user, id: 2 });
  queryClient.setQueryData(["sessions"], [{ id: 99 }]);
  return queryClient;
}

/** Hook'u verilen sorgu istemcisiyle çalıştıran sarmalayıcıyı üretir. */
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

afterEach(cleanup);

describe("auth api", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  test("401 yanıtında oturumu null olarak döndürür", async () => {
    getMock.mockResolvedValue({ error: { code: "AUTH_REQUIRED" }, response: { status: 401 } });
    const queryClient = new QueryClient();

    const { result } = renderHook(() => useMe(), { wrapper: createWrapper(queryClient) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  test("sunucu hatasında durum kodunu taşıyan hata fırlatır", async () => {
    getMock.mockResolvedValue({ error: { code: "INTERNAL_ERROR" }, response: { status: 500 } });
    const queryClient = new QueryClient();

    const { result } = renderHook(() => useMe(), { wrapper: createWrapper(queryClient) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).status).toBe(500);
  });

  test("girişte önceki kullanıcının önbelleğini siler", async () => {
    postMock.mockResolvedValue({ data: user, response: { status: 200 } });
    const queryClient = createQueryClientWithPreviousUser();

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper(queryClient) });
    await result.current.mutateAsync({ email: user.email, password: "password-123" });

    expect(queryClient.getQueryData(authKeys.me)).toEqual(user);
    expect(queryClient.getQueryData(["sessions"])).toBeUndefined();
  });

  test("çıkışta kullanıcıya ait bütün önbelleği siler", async () => {
    postMock.mockResolvedValue({ response: { status: 204 } });
    const queryClient = createQueryClientWithPreviousUser();

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper(queryClient) });
    await result.current.mutateAsync();

    expect(queryClient.getQueryData(authKeys.me)).toBeNull();
    expect(queryClient.getQueryData(["sessions"])).toBeUndefined();
  });

  test("çıkış başarısızsa önbelleğe dokunmaz ve hata fırlatır", async () => {
    postMock.mockResolvedValue({ error: { code: "INTERNAL_ERROR" }, response: { status: 500 } });
    const queryClient = createQueryClientWithPreviousUser();

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper(queryClient) });

    await expect(result.current.mutateAsync()).rejects.toBeInstanceOf(ApiError);
    expect(queryClient.getQueryData(["sessions"])).toEqual([{ id: 99 }]);
  });

  test("oturum düştüğünde önbelleği temizler", () => {
    const queryClient = createQueryClientWithPreviousUser();

    clearSessionOnUnauthorized(queryClient, new ApiError({ code: "AUTH_REQUIRED" }, 401));

    expect(queryClient.getQueryData(authKeys.me)).toBeNull();
    expect(queryClient.getQueryData(["sessions"])).toBeUndefined();
  });

  test("401 dışındaki hatada önbelleği korur", () => {
    const queryClient = createQueryClientWithPreviousUser();

    clearSessionOnUnauthorized(queryClient, new ApiError({ code: "INTERNAL_ERROR" }, 500));

    expect(queryClient.getQueryData(["sessions"])).toEqual([{ id: 99 }]);
  });
});
