/**
 * Öğrencinin test sorularını çözdüğü, anlık doğruluk ve kazanım gördüğü ekranı sunar.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, Link, useNavigate, useParams } from "react-router";
import ActionButton from "../../../components/ActionButton";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useCompleteSession, useStartSession, useSubmitAnswer } from "../api";
import ExplanationSection from "../components/ExplanationSection";
import HintChatPanel from "../components/HintChatPanel";
import QuestionCard, { type QuestionAnswerState } from "../components/QuestionCard";
import { useQuestionHints } from "../useQuestionHints";
import { useTutorChat } from "../useTutorChat";

/**
 * Oturumu açar, kaldığı sorudan başlatır ve sorular arası geçişi yönetir.
 */
export default function SolvePage() {
  const { t } = useTranslation("test");
  const { testId } = useParams();
  const navigate = useNavigate();
  const startSession = useStartSession();
  const submitAnswer = useSubmitAnswer();
  const completeSession = useCompleteSession();
  const hints = useQuestionHints();
  const chat = useTutorChat();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, QuestionAnswerState>>({});
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);

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
          if (!response.isCorrect) {
            setIsExplanationOpen(true);
          }
        },
      },
    );
  }

  /** Sorunun ipucunu ister ve gelen ipucunu sohbete ekler. */
  function handleRequestHint() {
    if (!currentQuestion) {
      return;
    }

    hints.requestHint(currentQuestion.id, (hintText) =>
      chat.addExchange(t("solve.hintUserMessage"), hintText),
    );
  }

  /** Öğrencinin yazdığı mesajı var olan sohbete ya da yeni açılan sohbete gönderir. */
  function handleSendMessage(text: string) {
    if (!sessionId || !currentQuestion) {
      return;
    }

    if (chat.conversationId) {
      void chat.sendMessage(text);
    } else {
      void chat.startChat(sessionId, currentQuestion.id, text);
    }
  }

  /** Oturumu tamamlar ve sonuç sayfasına yönlendirir. */
  function handleCompleteTest() {
    if (!sessionId || !testId) {
      return;
    }

    completeSession.mutate(sessionId, {
      /** Başarılı tamamlamada sonuç sayfasına geçer. */
      onSuccess: () => {
        navigate(generatePath(ROUTES.testResult, { sessionId: String(sessionId) }));
      },
    });
  }

  /** Verilen soruya geçer ve önceki cevap hatasını temizler. */
  function goToQuestion(index: number) {
    submitAnswer.reset();
    hints.reset();
    chat.reset();
    setIsExplanationOpen(false);
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
    <section className="mx-auto max-w-6xl space-y-6">
      <PageMeta title={questionLabel} description={t("solve.metaDescription")} />
      <div className="flex items-center justify-between border-b border-border pb-4">
        <Link to={ROUTES.tests} className="text-sm font-medium text-info hover:underline">
          {t("solve.backToTests")}
        </Link>
        <span className="text-sm font-medium text-heading">{questionLabel}</span>
      </div>

      <div className="space-y-1.5">
        <div className="h-2 w-full overflow-hidden rounded-full bg-navy-soft">
          <div
            className="h-full rounded-full bg-info transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          {t("solve.progressText", { percent: progressPercent })}
        </p>
      </div>

      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(380px,460px)]">
        <div className="space-y-6">
          <QuestionCard
            question={currentQuestion}
            answer={answers[currentQuestion.id]}
            onSelectOption={handleSelectOption}
            isSubmitting={submitAnswer.isPending}
            isExplanationOpen={isExplanationOpen}
            onToggleExplanation={() => setIsExplanationOpen((previous) => !previous)}
            onRequestHint={handleRequestHint}
            isHintPending={hints.isPending}
          />

          {submitAnswer.isPending && (
            <p className="text-sm text-muted-foreground">{t("solve.submitting")}</p>
          )}
          {submitAnswer.isError && (
            <p role="alert" className="rounded-xl bg-danger-soft p-3 text-sm text-destructive">
              {getProblemMessage(submitAnswer.error)}
            </p>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-6">
            <Button
              variant="outline"
              className="h-10 rounded-xl px-5"
              onClick={() => goToQuestion(currentIndex - 1)}
              disabled={currentIndex === 0}
            >
              {t("solve.prev")}
            </Button>
            {currentIndex === questions.length - 1 ? (
              <ActionButton onClick={handleCompleteTest} disabled={completeSession.isPending}>
                {completeSession.isPending ? t("solve.finishing") : t("solve.finishTest")}
              </ActionButton>
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

        <div className="lg:sticky lg:top-6">
          {isExplanationOpen && sessionId ? (
            <ExplanationSection sessionId={sessionId} questionId={currentQuestion.id} />
          ) : (
            <HintChatPanel
              messages={chat.messages}
              error={hints.error ?? chat.error}
              isHintPending={hints.isPending}
              isStreaming={chat.isStreaming}
              isLimitReached={chat.isLimitReached}
              onRequestHint={handleRequestHint}
              onSendMessage={handleSendMessage}
            />
          )}
        </div>
      </div>
    </section>
  );
}
