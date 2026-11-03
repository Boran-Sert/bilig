/**
 * Öğrencinin test sorularını çözdüğü, anlık doğruluk ve kazanım gördüğü ekranı sunar.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useStartSession, useSubmitAnswer } from "../api";
import QuestionCard, { type QuestionAnswerState } from "../components/QuestionCard";

/**
 * Oturumu açar, kaldığı sorudan başlatır ve sorular arası geçişi yönetir.
 */
export default function SolvePage() {
  const { t } = useTranslation("test");
  const { testId } = useParams();
  const startSession = useStartSession();
  const submitAnswer = useSubmitAnswer();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, QuestionAnswerState>>({});

  useEffect(() => {
    if (testId) {
      startSession.mutate(Number(testId), {
        /** Oturum açılınca kaldığı soruya geçer. */
        onSuccess: (session) => {
          const index = session.questions.findIndex(
            (question) => question.position === session.currentPosition,
          );
          setCurrentIndex(Math.max(index, 0));
        },
      });
    }
  }, [testId]);

  const questions = startSession.data?.questions ?? [];
  const currentQuestion = questions[currentIndex];
  const sessionId = startSession.data?.sessionId;

  /** Seçilen cevabı kaydeder ve sunucunun sonucunu saklar. */
  function handleSelectOption(option: string) {
    if (!sessionId || !currentQuestion) {
      return;
    }

    submitAnswer.mutate(
      { sessionId, questionId: currentQuestion.id, request: { selectedOption: option } },
      {
        /** Sunucunun doğru/yanlış sonucunu soruya bağlar. */
        onSuccess: (response) => {
          setAnswers((previous) => ({
            ...previous,
            [currentQuestion.id]: { selectedOption: option, response },
          }));
        },
      },
    );
  }

  /** Verilen soruya geçer ve önceki cevap hatasını temizler. */
  function goToQuestion(index: number) {
    submitAnswer.reset();
    setCurrentIndex(index);
  }

  if (startSession.isPending) {
    return (
      <div className="py-20 text-center text-sm text-muted-foreground">{t("solve.loading")}</div>
    );
  }

  if (startSession.isError) {
    return (
      <div role="alert" className="py-12 text-center text-sm text-destructive">
        {getProblemMessage(startSession.error)}
      </div>
    );
  }

  if (!currentQuestion) {
    return null;
  }

  const answeredCount = questions.filter(
    (question) => answers[question.id] !== undefined || question.selectedOption !== null,
  ).length;
  const progressPercent = Math.round((answeredCount / questions.length) * 100);
  const questionLabel = t("solve.questionNumber", {
    current: currentQuestion.position,
    total: questions.length,
  });

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <PageMeta title={questionLabel} description={t("solve.metaDescription")} />
      <div className="flex items-center justify-between border-b border-border pb-4">
        <Link to={ROUTES.tests} className="text-sm font-medium hover:underline">
          {t("solve.backToTests")}
        </Link>
        <span className="text-sm font-medium text-muted-foreground">{questionLabel}</span>
      </div>

      <div className="space-y-1.5">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          {t("solve.progressText", { percent: progressPercent })}
        </p>
      </div>

      <QuestionCard
        question={currentQuestion}
        answer={answers[currentQuestion.id]}
        onSelectOption={handleSelectOption}
        isSubmitting={submitAnswer.isPending}
      />

      {submitAnswer.isPending && (
        <p className="text-sm text-muted-foreground">{t("solve.submitting")}</p>
      )}
      {submitAnswer.isError && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {getProblemMessage(submitAnswer.error)}
        </p>
      )}

      <div className="flex justify-end gap-2 border-t border-border pt-6">
        <Button
          variant="outline"
          size="sm"
          onClick={() => goToQuestion(currentIndex - 1)}
          disabled={currentIndex === 0}
        >
          {t("solve.prev")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => goToQuestion(currentIndex + 1)}
          disabled={currentIndex === questions.length - 1}
        >
          {t("solve.next")}
        </Button>
      </div>
    </section>
  );
}
