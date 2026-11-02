/**
 * API istemcisinin CSRF ve yetkisiz yanıt davranışlarını test eder.
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createApiClient } from "./client";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
  document.cookie = "XSRF-TOKEN=; Max-Age=0; path=/";
});

/**
 * Testlerde kullanılacak API istemcisini oluşturur.
 * @returns Yapılandırılmış API istemcisi.
 */
function createTestClient() {
  return createApiClient({
    baseUrl: "http://localhost",
  });
}

test("GET isteğine CSRF başlığı eklemez", async () => {
  document.cookie = "XSRF-TOKEN=test-token; path=/";

  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  const client = createTestClient();

  await client.GET("/test" as never);

  const request = fetchMock.mock.calls[0]?.[0] as Request;
  expect(request.headers.get("X-XSRF-TOKEN")).toBeNull();
});

test("POST isteğine CSRF başlığı ekler", async () => {
  document.cookie = "XSRF-TOKEN=test-token; path=/";

  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  const client = createTestClient();

  await client.POST("/test" as never);

  const request = fetchMock.mock.calls[0]?.[0] as Request;
  expect(request.headers.get("X-XSRF-TOKEN")).toBe("test-token");
});

test("401 yanıtını otomatik yönlendirme yapmadan döndürür", async () => {
  fetchMock.mockResolvedValue(new Response(null, { status: 401 }));

  const client = createTestClient();

  const { response } = await client.GET("/test" as never);

  expect(response.status).toBe(401);
});
