/**
 * İçerik yönetimi kaynak yükleme işlemlerini TanStack Query hook'larıyla sunar.
 */
import { useMutation } from "@tanstack/react-query";
import { client } from "../../lib/api/client";
import { ApiError } from "../../lib/api/problem";
import type { UploadResponse } from "./types";

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
