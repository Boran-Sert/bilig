/**
 * Sunucunun yükleme cevabındaki dosyaları sonucuyla listeler.
 */
import { useTranslation } from "react-i18next";
import { cn } from "../../../lib/utils";
import type { UploadedFile } from "../types";

interface UploadResultListProps {
  files: UploadedFile[];
}

/**
 * Her dosya için yüklendi ya da daha önce yüklenmiş sonucunu gösterir.
 * @param props Sunucunun döndürdüğü dosyalar.
 * @returns Sonuç tablosu.
 */
export default function UploadResultList({ files }: UploadResultListProps) {
  const { t } = useTranslation("admin");

  return (
    <div className="space-y-3 pt-4">
      <div className="grid grid-cols-12 border-b border-border pb-2 text-xs font-semibold text-muted-foreground uppercase">
        <span className="col-span-8">{t("sources.table.file")}</span>
        <span className="col-span-4">{t("sources.table.result")}</span>
      </div>
      <ul className="divide-y divide-border">
        {files.map((file, index) => (
          <li key={file.sourceId ?? index} className="grid grid-cols-12 items-center py-3 text-sm">
            <span className="col-span-8 font-medium">{file.fileName}</span>
            <span className="col-span-4">
              <span
                className={cn(
                  "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
                  file.duplicate
                    ? "bg-secondary text-secondary-foreground"
                    : "bg-primary/10 text-primary",
                )}
              >
                {file.duplicate ? t("sources.result.duplicate") : t("sources.result.uploaded")}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
