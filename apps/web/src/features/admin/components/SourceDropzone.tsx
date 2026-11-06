/**
 * PDF dosyalarını sürükle-bırak ya da dosya seçiciyle alan bölge.
 */
import { type FileRejection, useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";

interface SourceDropzoneProps {
  isUploading: boolean;
  onDrop: (acceptedFiles: File[], rejectedFiles: FileRejection[]) => void;
}

/**
 * Sadece PDF kabul eden çoklu dosya bırakma alanını gösterir.
 * @param props Yükleme durumu ve bırakılan dosyaları alan fonksiyon.
 * @returns Dosya bırakma alanı.
 */
export default function SourceDropzone({ isUploading, onDrop }: SourceDropzoneProps) {
  const { t } = useTranslation("admin");
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
    noClick: true,
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-card p-12 text-center transition-colors",
        isDragActive ? "border-info bg-info-soft" : "border-input hover:border-info",
        isUploading && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />
      <p className="text-lg font-semibold text-heading">
        {isDragActive ? t("sources.dropActive") : t("sources.dropTitle")}
      </p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{t("sources.dropDescription")}</p>
      <Button
        type="button"
        variant="outline"
        className="mt-4 h-10 rounded-xl px-5"
        onClick={open}
        disabled={isUploading}
      >
        {isUploading ? t("sources.uploading") : t("sources.selectButton")}
      </Button>
    </div>
  );
}
