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
        "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors",
        isDragActive
          ? "border-primary bg-primary/5"
          : "border-border hover:border-muted-foreground/50",
        isUploading && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />
      <p className="text-base font-semibold">
        {isDragActive ? t("sources.dropActive") : t("sources.dropTitle")}
      </p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{t("sources.dropDescription")}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-4"
        onClick={open}
        disabled={isUploading}
      >
        {isUploading ? t("sources.uploading") : t("sources.selectButton")}
      </Button>
    </div>
  );
}
