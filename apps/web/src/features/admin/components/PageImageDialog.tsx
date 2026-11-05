/**
 * Kaynak sayfasının görüntüsünü tam boyutlu modal pencerede gösterir.
 */
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";

interface PageImageDialogProps {
  pageId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Sayfa görselini sunucudan çekip modal içinde sunar.
 */
export default function PageImageDialog({ pageId, isOpen, onClose }: PageImageDialogProps) {
  const { t } = useTranslation("admin");

  useEffect(() => {
    /** Escape tuşuna basıldığında modalı kapatır. */
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

  if (!isOpen || pageId === null) {
    return null;
  }

  const imageUrl = `/api/pages/${pageId}/image`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[90vh] max-w-4xl flex-col rounded-lg bg-card p-4 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-semibold">{t("review.openPage")}</span>
          <Button variant="ghost" size="sm" onClick={onClose}>
            {t("review.outcomes.cancel")}
          </Button>
        </div>
        <div className="overflow-auto">
          <img
            src={imageUrl}
            alt={t("review.openPage")}
            className="h-auto max-h-[75vh] w-auto rounded object-contain"
          />
        </div>
      </div>
    </div>
  );
}
