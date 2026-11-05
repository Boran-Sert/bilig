/**
 * Anlatımda kaynak gösterilen ders kitabı bloğunu ve Sayfayı aç butonunu sunar.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { useBlock } from "../api";
import PageImageDialog from "./PageImageDialog";

interface CitationCardProps {
  blockId: number;
}

/**
 * Veritabanındaki orijinal blok metnini çeker ve kaynak kartı olarak çizer.
 */
export default function CitationCard({ blockId }: CitationCardProps) {
  const { t } = useTranslation("test");
  const { data: block, isPending } = useBlock(blockId);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  if (isPending) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 text-xs text-muted-foreground animate-pulse">
        {t("solve.citationLoading")}
      </div>
    );
  }

  if (!block || !block.markdown) {
    return null;
  }

  const pageLabel = block.pageNo ? t("solve.pageNumber", { page: block.pageNo }) : "";
  const headerText = `${t("solve.textbookHeader")} · ${block.sourceTitle ?? ""} · ${pageLabel}`;

  return (
    <>
      <div className="space-y-2 rounded-lg border border-border bg-card p-3.5 shadow-xs">
        <div className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          {headerText}
        </div>

        <blockquote className="border-l-2 border-primary/50 py-0.5 pl-3 text-xs leading-relaxed italic text-foreground">
          &ldquo;{block.markdown}&rdquo;
        </blockquote>

        <div className="pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsDialogOpen(true)}
            disabled={!block.pageId}
          >
            {t("solve.openPage")}
          </Button>
        </div>
      </div>

      <PageImageDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        pageId={block.pageId ?? null}
        sourceTitle={block.sourceTitle}
        pageNo={block.pageNo}
      />
    </>
  );
}
