/**
 * Tamamlanan testin sorularını doğru cevaplar ve anlatımlarla birlikte inceletir.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, Link, useParams } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { linkButtonClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";
import { useSessionReview } from "../api";
import ExplanationSection from "../components/ExplanationSection";
import QuestionCard, { type QuestionAnswerState } from "../components/QuestionCard";
import type { ReviewQuestion } from "../types";

/** İnceleme sorusunu soru kartının beklediği cevap durumuna çevirir. */
function toAnswerState(question: ReviewQuestion): QuestionAnswerState {
  return {
    selectedOption: question.selectedOption ?? "",
    response: {
      isCorrect: question.isCorrect ?? false,
      correctOption: question.correctOption,
      outcomes: question.outcomes,
    },
  };
}

/**
 * Soruları tek tek, doğru ve yanlış şıklar işaretli olarak gösterir; yanlışlarda anlatım açılır.
 */
export default function SessionReviewPage() {
  const { t } = useTranslation("test");
  const { sessionId } = useParams();
  const review = useSessionReview(Number(sessionId));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);

  if (review.isPending) {
    return <p className="py-20 text-center text-sm text-muted-foreground">{t("review.loading")}</p>;
  }

  const questions = review.data?.questions ?? [];
  const question = questions[currentIndex];
  const resultPath = generatePath(ROUTES.testResult, { sessionId: String(sessionId) });

  if (review.isError || !question) {
    return (
      <section className="mx-auto max-w-xl space-y-4 py-12 text-center">
        <p role="alert" className="text-sm text-destructive">
          {review.isError ? getProblemMessage(review.error) : t("review.notFound")}
        </p>
        <Link to={resultPath} className={linkButtonClass("outline")}>
          {t("review.backToResult")}
        </Link>
      </section>
    );
  }

  const isBlank = question.selectedOption === null;
  const isLast = currentIndex === questions.length - 1;
  const questionLabel = t("solve.questionNumber", {
    current: question.position,
    total: questions.length,
  });

  /** Verilen soruya geçer ve açık anlatımı kapatır. */
  function goToQuestion(index: number) {
    setIsExplanationOpen(false);
    setCurrentIndex(index);
  }

  return (
    <section
      className={`mx-auto ${isExplanationOpen ? "max-w-6xl" : "max-w-3xl"} space-y-6 transition-all duration-200`}
    >
      <PageMeta title={questionLabel} description={t("review.metaDescription")} />
      <div className="flex items-center justify-between border-b border-border pb-4">
        <Link to={resultPath} className="text-sm font-medium text-info hover:underline">
          {t("review.backToResult")}
        </Link>
        <span className="text-sm font-medium text-heading">{questionLabel}</span>
      </div>

      <div
        className={
          isExplanationOpen
            ? "grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(380px,460px)]"
            : "space-y-6"
        }
      >
        <div className="space-y-6">
          <QuestionCard
            question={question}
            answer={toAnswerState(question)}
            onSelectOption={() => undefined}
            isSubmitting={false}
            isExplanationOpen={isExplanationOpen}
            onToggleExplanation={() => setIsExplanationOpen((previous) => !previous)}
            canExplain={!isBlank && question.isCorrect === false}
          />
          {isBlank && <p className="text-sm text-muted-foreground">{t("review.blankNote")}</p>}

          <div className="flex justify-end gap-2 border-t border-border pt-6">
            <Button
              variant="outline"
              className="h-10 rounded-xl px-5"
              onClick={() => goToQuestion(currentIndex - 1)}
              disabled={currentIndex === 0}
            >
              {t("solve.prev")}
            </Button>
            {isLast ? (
              <Link to={resultPath} className={linkButtonClass("default")}>
                {t("review.backToResult")}
              </Link>
            ) : (
              <Button
                variant="outline"
                className="h-10 rounded-xl px-5"
                onClick={() => goToQuestion(currentIndex + 1)}
              >
                {t("solve.next")}
              </Button>
            )}
          </div>
        </div>

        {isExplanationOpen && sessionId && (
          <div className="lg:sticky lg:top-6">
            <ExplanationSection sessionId={Number(sessionId)} questionId={question.id} />
          </div>
        )}
      </div>
    </section>
  );
}
