/**
 * Öğrencinin test sorularını çözdüğü, anlık doğruluk ve kazanım gördüğü ekranı sunar.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import Markdown from "../../../components/Markdown";
import OptionBubble, { type OptionStatus } from "../../../components/OptionBubble";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useStartSession, useSubmitAnswer } from "../api";
import type { AnswerResponse, SessionQuestion } from "../types";

interface QuestionAnswerState {
  selectedOption: string;
  response?: AnswerResponse;
}

/**
 * Tek bir soru kartını, parçasını, şıklarını ve kazanımlarını oluşturur.
 */
function QuestionCard({
  question,
  answer,
  onSelectOption,
  isSubmitting,
}: {
  question: SessionQuestion;
  answer?: QuestionAnswerState;
  onSelectOption: (option: string) => void;
  isSubmitting: boolean;
}) {
  const { t } = useTranslation("test");
  const isAnswered = answer?.response !== undefined || question.selectedOption !== null;

  return (
    <div className="space-y-6">
      {question.content.passage && question.content.passage.length > 0 && (
        <div className="rounded-lg border border-border bg-muted/30 p-5">
          {question.content.passage.map((block, idx) => (
            <Markdown key={idx} content={block.md} className="text-sm leading-relaxed" />
          ))}
        </div>
      )}

      <div className="space-y-2">
        <span className="font-semibold">{question.position}. </span>
        {question.content.stem.map((block, idx) => (
          <Markdown key={idx} content={block.md} className="inline font-medium" />
        ))}
      </div>

      <div className="space-y-3 pt-2">
        {question.content.options.map((option) => {
          const selected =
            answer?.selectedOption === option.label || question.selectedOption === option.label;
          const isCorrectOption = answer?.response?.correctOption === option.label;
          let status: OptionStatus = "default";
          let borderClasses = "border-border hover:border-muted-foreground/50";
          let badge: string | null = null;

          if (isAnswered) {
            if (isCorrectOption) {
              status = "correct";
              borderClasses = "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20";
              badge = t("solve.correctAnswer");
            } else if (selected && answer?.response?.isCorrect === false) {
              status = "wrong";
              borderClasses = "border-destructive bg-destructive/5";
              badge = t("solve.yourAnswer");
            }
          } else if (selected) {
            status = "selected";
          }

          return (
            <button
              key={option.label}
              type="button"
              disabled={isAnswered || isSubmitting}
              onClick={() => onSelectOption(option.label)}
              className={`flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors ${borderClasses} ${
                isAnswered ? "cursor-default" : "cursor-pointer"
              }`}
            >
              <div className="flex items-center gap-3">
                <OptionBubble label={option.label} status={status} />
                <Markdown content={option.blocks[0]?.md ?? ""} className="text-sm" />
              </div>
              {badge && (
                <span
                  className={`text-xs font-semibold ${
                    isCorrectOption ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"
                  }`}
                >
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {answer?.response?.outcomes && answer.response.outcomes.length > 0 && (
        <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">{t("solve.outcomesLabel")} </span>
          {answer.response.outcomes.map((o) => `${o.code} ${o.title}`).join(" · ")}
        </div>
      )}
    </div>
  );
}

/**
 * Öğrencinin test çözme sayfasını yönetir ve sorular arası geçişi sağlar.
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
        /** Oturum başladığında kaldığı soruyu ayarlar. */
        onSuccess: (data) => {
          const pos = data.currentPosition;
          const foundIdx = data.questions.findIndex((q) => q.position === pos);
          setCurrentIndex(foundIdx >= 0 ? foundIdx : 0);
        },
      });
    }
  }, [testId]);

  const questions = startSession.data?.questions ?? [];
  const currentQuestion = questions[currentIndex];
  const sessionId = startSession.data?.sessionId;

  /** Seçilen cevabı kaydeder ve yanıtı saklar. */
  function handleSelectOption(option: string) {
    if (!sessionId || !currentQuestion) {
      return;
    }

    submitAnswer.mutate(
      {
        sessionId,
        questionId: currentQuestion.id,
        request: { selectedOption: option },
      },
      {
        /** Cevap başarıyla kaydedildiğinde cevabı saklar. */
        onSuccess: (response) => {
          setAnswers((prev) => ({
            ...prev,
            [currentQuestion.id]: { selectedOption: option, response },
          }));
        },
      },
    );
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

  const answeredCount =
    Object.keys(answers).length +
    questions.filter((q) => q.selectedOption && !answers[q.id]).length;
  const progressPercent = Math.round((answeredCount / Math.max(questions.length, 1)) * 100);

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <PageMeta
        title={t("solve.questionNumber", {
          current: currentQuestion.position,
          total: questions.length,
        })}
        description={t("solve.questionNumber", {
          current: currentQuestion.position,
          total: questions.length,
        })}
      />
      <div className="flex items-center justify-between border-b border-border pb-4">
        <Link to={ROUTES.tests} className="text-sm font-medium hover:underline">
          {t("solve.backToTests")}
        </Link>
        <span className="text-sm font-medium text-muted-foreground">
          {t("solve.questionNumber", {
            current: currentQuestion.position,
            total: questions.length,
          })}
        </span>
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

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6">
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled>
            {t("solve.hint")}
          </Button>
          <Button variant="default" size="sm" disabled className="bg-blue-600 hover:bg-blue-700">
            {t("solve.whyWrong")}
          </Button>
          <Button variant="outline" size="sm" disabled>
            {t("solve.similar")}
          </Button>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
          >
            {t("solve.prev")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))}
            disabled={currentIndex === questions.length - 1}
          >
            {t("solve.next")}
          </Button>
        </div>
      </div>

      <div className="pt-2 text-center">
        <button type="button" className="text-xs text-muted-foreground hover:underline">
          {t("solve.report")}
        </button>
      </div>
    </section>
  );
}
