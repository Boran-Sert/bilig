/**
 * İçerik yönetimi kaynak yükleme ve listeleme işlemlerini TanStack Query hook'larıyla sunar.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import {
  ANSWER_KEY_LIST_SIZE,
  SOURCES_PAGE_SIZE,
  SOURCES_POLL_INTERVAL_MS,
} from "../../lib/constants";
import type {
  ReprocessRequest,
  SourceListItem,
  SourceListResponse,
  UploadRequest,
  UploadResponse,
} from "./types";

export const adminKeys = {
  sources: ["admin", "sources"] as const,
  answerKeys: ["admin", "sources", "ANSWER_KEY"] as const,
};

/**
 * Listede hâlâ işlenmekte olan dosya olup olmadığını kontrol eder.
 */
export function hasProcessingSources(items: SourceListItem[] = []): boolean {
  return items.some((item) => item.status === "UPLOADED" || item.status === "PROCESSING");
}

/**
 * Kaynak listesini sunucudan çeker; işlenen dosya varken 3 saniyede bir yeniler.
 */
export function useSources(enabled: boolean, page = 0, size = SOURCES_PAGE_SIZE) {
  return useQuery<SourceListResponse, ApiError>({
    queryKey: [...adminKeys.sources, page, size] as const,
    enabled,
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
 * Teste bağlanabilecek cevap anahtarı kaynaklarını çeker.
 */
export function useAnswerKeys(enabled: boolean) {
  return useQuery<SourceListItem[], ApiError>({
    queryKey: adminKeys.answerKeys,
    enabled,
    /** Cevap anahtarı türündeki kaynakları GET /api/admin/sources ucundan çeker. */
    queryFn: async (): Promise<SourceListItem[]> => {
      const { data, error, response } = await client.GET("/api/admin/sources", {
        params: { query: { page: 0, size: ANSWER_KEY_LIST_SIZE, kind: "ANSWER_KEY" } },
      });

      const status = response.status;

      if (error || !data) {
        throw new ApiError(error, status);
      }

      return data.items;
    },
  });
}

/**
 * Kaynağı yeniden işlenmek üzere kuyruğa koyar; verilirse önce cevap anahtarını bağlar.
 */
export function useReprocessSource() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, ReprocessRequest>({
    /** POST /api/admin/sources/{id}/reprocess ucunu çağırır. */
    mutationFn: async ({ sourceId, answerKeySourceId }: ReprocessRequest): Promise<void> => {
      const { error, response } = await client.POST("/api/admin/sources/{id}/reprocess", {
        params: { path: { id: sourceId }, query: { answerKeySourceId } },
      });

      const status = response.status;

      if (error || !response.ok) {
        throw new ApiError(error, status);
      }
    },
    /** Kaynağın yeni durumunun görünmesi için listeyi yeniler. */
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminKeys.sources }),
  });
}

/**
 * Birden fazla PDF dosyasını tek istekte multipart form olarak sunucuya yükler.
 */
export function useUploadSources() {
  const queryClient = useQueryClient();

  return useMutation<UploadResponse, ApiError, UploadRequest>({
    /** Dosyaları seçilen türle bodySerializer ile FormData'ya dönüştürerek sunucuya gönderir. */
    mutationFn: async ({
      files,
      kind,
      answerKeySourceId,
    }: UploadRequest): Promise<UploadResponse> => {
      const { data, error, response } = await client.POST("/api/admin/sources", {
        params: { query: { kind, answerKeySourceId } },
        // Sadece tip için
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
    /** Yeni dosyaların listede görünmesi için kaynak listesini yeniler. */
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminKeys.sources }),
  });
}
