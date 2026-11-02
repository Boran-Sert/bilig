/**
 * İçerik yönetimi kaynak yükleme ve listeleme işlemlerini TanStack Query hook'larıyla sunar.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import type { SourceListItem, SourceListResponse, UploadResponse } from "./types";

export const adminKeys = {
  sources: ["admin", "sources"] as const,
};

export const SOURCES_POLL_INTERVAL_MS = 3000;

/**
 * Listede hâlâ işlenmekte olan dosya olup olmadığını kontrol eder.
 * @param items Kaynak dosyaları listesi.
 * @returns İşlenen dosya varsa true.
 */
export function hasProcessingSources(items: SourceListItem[] = []): boolean {
  return items.some((item) => item.status === "UPLOADED" || item.status === "PROCESSING");
}

/**
 * Kaynak listesini sunucudan çeker; işlenen dosya varken 3 saniyede bir yeniler.
 * @param page Sayfa numarası (0 tabanlı).
 * @param size Sayfa başına kayıt sayısı.
 */
export function useSources(page = 0, size = 20) {
  return useQuery<SourceListResponse, ApiError>({
    queryKey: [...adminKeys.sources, page, size] as const,
    /** Kaynakları sayfalı olarak GET /api/admin/sources ucundan çeker. */
    queryFn: async (): Promise<SourceListResponse> => {
      const { data, error, response } = await client.GET("/api/admin/sources", {
        params: { query: { page, size } },
      });

      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
    /** İşlenen dosya varken 3 saniyede bir yeniler, yoksa yenilemeyi durdurur. */
    refetchInterval: (query) => {
      const data = query.state.data;
      return data && hasProcessingSources(data.items) ? SOURCES_POLL_INTERVAL_MS : false;
    },
  });
}

/**
 * Birden fazla PDF dosyasını tek istekte multipart form olarak sunucuya yükler.
 */
export function useUploadSources() {
  return useMutation<UploadResponse, ApiError, File[]>({
    /** Dosyaları bodySerializer ile FormData'ya dönüştürerek sunucuya gönderir. */
    mutationFn: async (files: File[]): Promise<UploadResponse> => {
      const { data, error, response } = await client.POST("/api/admin/sources", {
        body: { files: files.map((file) => file.name) },
        /** Dosyaları tarayıcının boundary ekleyeceği FormData nesnesine serileştirir. */
        bodySerializer: () => {
          const formData = new FormData();
          for (const file of files) {
            formData.append("files", file);
          }
          return formData;
        },
      });

      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data;
    },
  });
}
