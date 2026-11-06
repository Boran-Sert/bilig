/**
 * Tek bir sorunun parçasını, kökünü, şıklarını ve cevaptan sonra kazanımlarını gösterir.
 */
import { useTranslation } from "react-i18next";
import Markdown from "../../../components/Markdown";
import type { OptionStatus } from "../../../components/OptionBubble";
import { Button } from "../../../components/ui/button";
import type { AnswerResponse, SessionQuestion } from "../types";
import AnswerOption from "./AnswerOption";

export interface QuestionAnswerState {
  selectedOption: string;
  response: AnswerResponse;
}

interface QuestionCardProps {
  question: SessionQuestion;
  answer?: QuestionAnswerState;
  onSelectOption: (option: string) => void;
  isSubmitting: boolean;
  isExplanationOpen?: boolean;
  onToggleExplanation?: () => void;
  onRequestHint?: () => void;
  isHintPending?: boolean;
  canExplain?: boolean;
}

/** Şıkkın durumunu sunucunun cevap sonucuna göre belirler. */
function getOptionStatus(
  label: string,
  selectedOption: string | null,
  response?: AnswerResponse,
): OptionStatus {
  if (response?.correctOption === label) {
    return "correct";
  }
  if (selectedOption !== label) {
    return "default";
  }
  return response ? "wrong" : "selected";
}

/** Soruyu gösterir; cevaplanmış soruda şıkları kilitler. */
export default function QuestionCard({
  question,
  answer,
  onSelectOption,
  isSubmitting,
  isExplanationOpen,
  onToggleExplanation,
  onRequestHint,
  isHintPending,
  canExplain = true,
}: QuestionCardProps) {
  const { t } = useTranslation("test");
  const selectedOption = answer?.selectedOption ?? question.selectedOption;
  const isAnswered = selectedOption !== null;
  const outcomes = answer?.response.outcomes ?? [];
  const isWrongAnswer = answer?.response ? !answer.response.isCorrect : isAnswered;

  return (
    <div className="space-y-6">
      {question.content.passage && question.content.passage.length > 0 && (
        <div className="space-y-2 rounded-2xl border border-navy/10 bg-card p-6 text-sm leading-relaxed shadow-xs">
          {question.content.passage.map((block, blockIndex) => (
            <Markdown key={blockIndex} content={block.md} />
          ))}
        </div>
      )}

      <div className="flex gap-2 font-medium">
        <span className="font-semibold">{question.position}.</span>
        <div className="space-y-2">
          {question.content.stem.map((block, blockIndex) => (
            <Markdown key={blockIndex} content={block.md} />
          ))}
        </div>
      </div>

      <div className="space-y-3 pt-2">
        {question.content.options.map((option) => (
          <AnswerOption
            key={option.label}
            option={option}
            status={getOptionStatus(option.label, selectedOption, answer?.response)}
            disabled={isAnswered || isSubmitting}
            onSelect={() => onSelectOption(option.label)}
          />
        ))}
      </div>

      {outcomes.length > 0 && (
        <div className="rounded-xl bg-info-soft p-3 text-xs text-foreground">
          <span className="font-semibold text-heading">{t("solve.outcomesLabel")} </span>
          {outcomes.map((outcome) => `${outcome.code} ${outcome.title}`).join(" · ")}
        </div>
      )}

      {!isAnswered && (
        <Button
          type="button"
          variant="outline"
          disabled={isHintPending}
          onClick={onRequestHint}
          className="h-10 rounded-xl border-info/40 px-5 text-info"
        >
          {t("solve.hint")}
        </Button>
      )}

      {isAnswered && (
        <div className="space-y-3 border-t border-border/60 pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant={isExplanationOpen ? "default" : "outline"}
              className="h-10 rounded-xl px-5"
              onClick={onToggleExplanation}
              disabled={!isWrongAnswer || !canExplain}
            >
              {t("solve.whyWrong")}
            </Button>
            <Button variant="outline" className="h-10 rounded-xl px-5" disabled>
              {t("solve.similar")}
            </Button>
          </div>

          <div>
            <button
              type="button"
              className="text-xs text-muted-foreground hover:underline"
              disabled
            >
              {t("solve.report")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
