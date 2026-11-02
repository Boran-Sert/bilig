/**
 * İçerik yönetimi API tiplerini ve dosya yükleme durumlarını tanımlar.
 */
import type { components } from "../../lib/api/schema";

export type UploadedFile = components["schemas"]["UploadedFile"];
export type UploadResponse = components["schemas"]["UploadResponse"];

/**
 * Arayüzde listelenen dosyanın seçim ve yükleme durumunu tanımlar.
 */
export interface UploadItem {
  file: File;
  sourceId?: number;
  duplicate?: boolean;
  status: "idle" | "uploading" | "success" | "error";
  errorMessage?: string;
}
