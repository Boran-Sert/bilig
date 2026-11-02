/**
 * OpenAPI tabanlı API istemcisini yapılandırır.
 */
import createClient from "openapi-fetch";
import type { paths } from "./schema";

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/**
 * Belirtilen çerezin değerini döndürür.
 * @param name Aranan çerezin adı.
 * @returns Çerez değeri veya bulunamazsa undefined.
 */
function getCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

/**
 * API istemcisinin yapılandırma seçeneklerini tanımlar.
 */
interface ApiClientOptions {
  baseUrl?: string;
}

/**
 * Yapılandırılmış bir API istemcisi oluşturur.
 * @param options İstemci yapılandırma seçenekleri.
 * @returns İstek ara katmanları eklenmiş API istemcisi.
 */
export function createApiClient(options: ApiClientOptions = {}) {
  const api = createClient<paths>({
    baseUrl:
      options.baseUrl ??
      (typeof window === "undefined" ? "http://localhost" : window.location.origin),
    credentials: "include",
  });

  api.use({
    onRequest({ request }) {
      if (unsafeMethods.has(request.method.toUpperCase())) {
        const token = getCookie("XSRF-TOKEN");

        if (token) {
          request.headers.set("X-XSRF-TOKEN", token);
        }
      }

      return request;
    },

    onResponse({ response }) {
      return response;
    },
  });

  return api;
}

export const client = createApiClient();
