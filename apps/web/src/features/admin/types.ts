/**
 * İçerik yönetimi özelliğinin üretilmiş API tiplerine verdiği kısa adlar.
 */
import type { components, operations } from "../../lib/api/schema";

export type UploadedFile = components["schemas"]["UploadedFile"];
export type UploadResponse = components["schemas"]["UploadResponse"];
export type SourceListItem = components["schemas"]["SourceListItem"];
export type SourceListResponse = components["schemas"]["PageResponseSourceListItem"];
export type SourceKind = operations["upload"]["parameters"]["query"]["kind"];

/** Tek seferde yüklenen dosyalar, hepsinin türü ve testlerse cevap anahtarı kaynağı. */
export interface UploadRequest {
  files: File[];
  kind: SourceKind;
  answerKeySourceId?: number;
}

/** Yeniden işlenecek kaynak ve önce bağlanacak cevap anahtarı. */
export interface ReprocessRequest {
  sourceId: number;
  answerKeySourceId?: number;
}
