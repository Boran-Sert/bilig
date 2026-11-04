/**
 * Ders kitabı sayfasının orijinal PNG görüntüsünü modal diyalog olarak gösterir.
 */
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";

interface PageImageDialogProps {
  pageId: number | null;
  sourceTitle?: string;
  pageNo?: number;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Sayfa görüntüsü penceresini sunar; ESC tuşuyla veya kapat butonuyla kapanır.
 */
export default function PageImageDialog({
  pageId,
  sourceTitle,
  pageNo,
  isOpen,
  onClose,
}: PageImageDialogProps) {
  const { t } = useTranslation("test");

  useEffect(() => {
    /** ESC tuşuna basıldığında modalı kapatır. */
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !pageId) {
    return null;
  }

  const titleText = `${sourceTitle ?? ""} · ${t("solve.pageNumber", { page: pageNo ?? 1 })}`;
  const altText = t("solve.pageImageAlt", {
    source: sourceTitle ?? "",
    page: pageNo ?? 1,
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={titleText}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <span className="text-sm font-semibold tracking-tight">{titleText}</span>
          <Button variant="ghost" size="sm" onClick={onClose}>
            {t("solve.close")}
          </Button>
        </div>

        <div className="flex min-h-[300px] items-center justify-center overflow-auto p-4 bg-muted/20">
          <img
            src={`/api/pages/${pageId}/image`}
            alt={altText}
            className="max-h-[75vh] w-auto rounded object-contain shadow"
          />
        </div>
      </div>
    </div>
  );
}
