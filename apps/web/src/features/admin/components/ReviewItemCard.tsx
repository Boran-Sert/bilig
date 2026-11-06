/**
 * İnceleme listesindeki soru, paragraf veya kaynak kaydını kart şeklinde gösterir.
 */
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Markdown from "../../../components/Markdown";
import { Button } from "../../../components/ui/button";
import type { ReviewItemResponse } from "../types";
import OutcomeSelectorDialog from "./OutcomeSelectorDialog";
import ReviewProblemBadge from "./ReviewProblemBadge";

interface ReviewItemCardProps {
  item: ReviewItemResponse;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onFix: (id: number, outcomeIds: number[]) => void;
  onOpenPage: (pageId: number) => void;
  isPending?: boolean;
}

/** Markdown bloklarını veya metin dizilerini güvenle çizer. */
function renderMarkdownContent(blocks: unknown): ReactNode {
  if (typeof blocks === "string") {
    return <Markdown content={blocks} />;
  }
  if (Array.isArray(blocks)) {
    return blocks.map((b, idx) => (
      <Markdown
        key={idx}
        content={
          typeof b === "string"
            ? b
            : typeof b === "object" && b !== null && "md" in b
              ? String(b.md)
              : ""
        }
      />
    ));
  }
  return null;
}

/**
 * Kaydın türüne göre içeriği, sorunları ve onay/ret/düzelt aksiyonlarını sunar.
 */
export default function ReviewItemCard({
  item,
  onApprove,
  onReject,
  onFix,
  onOpenPage,
  isPending,
}: ReviewItemCardProps) {
  const { t } = useTranslation("admin");
  const [isFixDialogOpen, setIsFixDialogOpen] = useState(false);

  const isSource = item.targetType === "SOURCE";
  const currentOutcomeIds = item.outcomes.map((o) => o.id);

  /** Düzeltme diyaloğunda seçilen kazanımları kaydeder. */
  function handleSaveOutcomes(outcomeIds: number[]) {
    setIsFixDialogOpen(false);
    onFix(item.id, outcomeIds);
  }

  return (
    <article className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-info-soft px-3 py-1 text-xs font-semibold text-info-strong">
            {t(`review.targetTypes.${item.targetType}`)}
          </span>
          <span className="text-xs text-muted-foreground">
            {t(`review.reasons.${item.reason}`, { defaultValue: item.reason })}
          </span>
        </div>
        {item.pageId !== null && (
          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={() => item.pageId !== null && onOpenPage(item.pageId)}
          >
            {t("review.openPage")}
          </Button>
        )}
      </div>

      {item.targetType === "QUESTION" && item.questionContent && (
        <div className="space-y-3 text-sm">
          {item.questionContent.passage != null && (
            <div className="rounded-xl bg-background p-4 text-xs leading-relaxed">
              {renderMarkdownContent(item.questionContent.passage)}
            </div>
          )}
          {item.questionContent.stem != null && (
            <div className="font-medium">{renderMarkdownContent(item.questionContent.stem)}</div>
          )}
        </div>
      )}

      {item.targetType === "BLOCK" && item.blockMarkdown && (
        <div className="text-sm leading-relaxed">
          <Markdown content={item.blockMarkdown} />
        </div>
      )}

      {isSource && (
        <div className="space-y-3">
          <h3 className="font-semibold text-foreground">{item.sourceTitle}</h3>
          <div className="space-y-2">
            {item.problems.map((prob, idx) => (
              <ReviewProblemBadge key={idx} problem={prob} onOpenPage={onOpenPage} />
            ))}
          </div>
        </div>
      )}

      {!isSource && item.outcomes.length > 0 && (
        <div className="rounded-xl border border-dashed border-input p-3 text-xs">
          <span className="font-semibold text-muted-foreground">
            {t("review.outcomes.title")}:{" "}
          </span>
          <span className="text-foreground">
            {item.outcomes.map((o) => `${o.code} ${o.title}`).join(" · ")}
          </span>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => onReject(item.id)}
        >
          {t("review.actions.reject")}
        </Button>

        {!isSource && (
          <Button
            variant="outline"
            size="sm"
            disabled={isPending}
            onClick={() => setIsFixDialogOpen(true)}
          >
            {t("review.actions.fix")}
          </Button>
        )}

        <Button size="sm" disabled={isPending} onClick={() => onApprove(item.id)}>
          {t("review.actions.approve")}
        </Button>
      </div>

      {!isSource && (
        <OutcomeSelectorDialog
          isOpen={isFixDialogOpen}
          initialOutcomeIds={currentOutcomeIds}
          onSave={handleSaveOutcomes}
          onClose={() => setIsFixDialogOpen(false)}
        />
      )}
    </article>
  );
}
