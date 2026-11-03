/**
 * Tek bir sorunun parçasını, kökünü, şıklarını ve cevaptan sonra kazanımlarını gösterir.
 */
import { useTranslation } from "react-i18next";
import Markdown from "../../../components/Markdown";
import type { OptionStatus } from "../../../components/OptionBubble";
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
}: QuestionCardProps) {
  const { t } = useTranslation("test");
  const selectedOption = answer?.selectedOption ?? question.selectedOption;
  const isAnswered = selectedOption !== null;
  const outcomes = answer?.response.outcomes ?? [];

  return (
    <div className="space-y-6">
      {question.content.passage && question.content.passage.length > 0 && (
        <div className="space-y-2 rounded-lg border border-border bg-muted/30 p-5 text-sm leading-relaxed">
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
        <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">{t("solve.outcomesLabel")} </span>
          {outcomes.map((outcome) => `${outcome.code} ${outcome.title}`).join(" · ")}
        </div>
      )}
    </div>
  );
}
