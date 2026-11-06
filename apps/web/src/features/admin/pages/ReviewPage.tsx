/**
 * İçerik yöneticileri için inceleme listesini, sayfalama ve onay akışlarını sunar.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { SOURCES_PAGE_SIZE } from "../../../lib/constants";
import { useMe } from "../../auth/api";
import { useDecideReview, useReviews } from "../api";
import PageImageDialog from "../components/PageImageDialog";
import ReviewItemCard from "../components/ReviewItemCard";

/**
 * İnceleme bekleyen kayıtları listeleyen ana sayfa bileşeni.
 */
export default function ReviewPage() {
  const { t } = useTranslation("admin");
  const { data: user, isPending: isUserPending } = useMe();
  const [page, setPage] = useState(0);
  const [activePageId, setActivePageId] = useState<number | null>(null);

  const canManage = user?.canManageContent === true;
  const reviewsQuery = useReviews(canManage, page, SOURCES_PAGE_SIZE);
  const decideMutation = useDecideReview();

  if (isUserPending || !user) {
    return null;
  }

  if (!user.canManageContent) {
    return (
      <p role="alert" className="py-12 text-center text-sm font-medium text-destructive">
        {t("review.errors.accessDenied")}
      </p>
    );
  }

  const items = reviewsQuery.data?.items ?? [];
  const total = reviewsQuery.data?.total ?? 0;
  const totalPages = Math.ceil(total / SOURCES_PAGE_SIZE);

  return (
    <div className="space-y-6">
      <PageMeta title={t("review.title")} description={t("review.metaDescription")} />

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t("review.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("review.metaDescription")}</p>
        </div>
        {total > 0 && (
          <span className="rounded-full bg-navy-soft px-3 py-1 text-xs font-medium text-navy">
            {t("review.recordCount", { count: total })}
          </span>
        )}
      </header>

      {reviewsQuery.isPending && (
        <p className="py-8 text-center text-sm text-muted-foreground">{t("sources.loadingList")}</p>
      )}

      {reviewsQuery.isError && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {getProblemMessage(reviewsQuery.error)}
        </p>
      )}
      {decideMutation.isError && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {getProblemMessage(decideMutation.error)}
        </p>
      )}

      {!reviewsQuery.isPending && !reviewsQuery.isError && items.length === 0 && (
        <p className="rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
          {t("review.empty")}
        </p>
      )}

      <div className="space-y-4">
        {items.map((item) => (
          <ReviewItemCard
            key={item.id}
            item={item}
            isPending={decideMutation.isPending}
            onApprove={(id) => decideMutation.mutate({ id, request: { decision: "APPROVE" } })}
            onReject={(id) => decideMutation.mutate({ id, request: { decision: "REJECT" } })}
            onFix={(id, outcomeIds) =>
              decideMutation.mutate({ id, request: { decision: "FIX", outcomeIds } })
            }
            onOpenPage={(pageId) => setActivePageId(pageId)}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((prev) => Math.max(0, prev - 1))}
          >
            {t("review.pagination.prev")}
          </Button>
          <span className="px-2 text-xs text-muted-foreground">
            {page + 1} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((prev) => prev + 1)}
          >
            {t("review.pagination.next")}
          </Button>
        </div>
      )}

      <PageImageDialog
        pageId={activePageId}
        isOpen={activePageId !== null}
        onClose={() => setActivePageId(null)}
      />
    </div>
  );
}
