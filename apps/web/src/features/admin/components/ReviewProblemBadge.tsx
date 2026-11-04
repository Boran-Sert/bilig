/**
 * Kaynak doğrulama veya cevap anahtarı sorununu detaylarıyla gösterir.
 */
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import type { ReviewProblem } from "../types";

interface ReviewProblemBadgeProps {
  problem: ReviewProblem;
  onOpenPage?: (pageId: number) => void;
}

/**
 * Sorun kodunu ve konum bilgisini rozet olarak çizer.
 */
export default function ReviewProblemBadge({ problem, onOpenPage }: ReviewProblemBadgeProps) {
  const { t } = useTranslation("admin");
  const problemText = t(`review.problems.${problem.code}`, { defaultValue: problem.code });

  const hasLocation = problem.test !== null || problem.number !== null || problem.pageNo !== null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-muted/40 px-3 py-2 text-xs">
      <div className="space-y-1">
        <span className="font-semibold text-destructive">{problemText}</span>
        {hasLocation && (
          <p className="text-muted-foreground">
            {t("review.problemLocation", {
              test: problem.test ?? "-",
              number: problem.number ?? "-",
              page: problem.pageNo ?? "-",
            })}
          </p>
        )}
      </div>
      {problem.pageId !== null && onOpenPage && (
        <Button
          type="button"
          variant="outline"
          size="xs"
          onClick={() => problem.pageId !== null && onOpenPage(problem.pageId)}
        >
          {t("review.openPage")}
        </Button>
      )}
    </div>
  );
}
