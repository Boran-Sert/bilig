/**
 * Soru şıkkını harf balonu, metni ve sonuç etiketiyle düğme olarak gösterir.
 */
import { useTranslation } from "react-i18next";
import Markdown from "../../../components/Markdown";
import OptionBubble, { type OptionStatus } from "../../../components/OptionBubble";
import type { QuestionOption } from "../types";

interface AnswerOptionProps {
  option: QuestionOption;
  status: OptionStatus;
  disabled: boolean;
  onSelect: () => void;
}

const BORDER_CLASSES: Record<OptionStatus, string> = {
  default: "border-border bg-card hover:border-info hover:bg-info-soft/50",
  selected: "border-navy bg-navy-soft",
  correct: "border-success bg-success-soft",
  wrong: "border-destructive bg-danger-soft",
};

const BADGE_COLORS: Record<OptionStatus, string> = {
  default: "",
  selected: "text-navy",
  correct: "text-success",
  wrong: "text-destructive",
};

const BADGE_KEYS: Partial<Record<OptionStatus, string>> = {
  selected: "solve.yourAnswer",
  correct: "solve.correctAnswer",
  wrong: "solve.yourAnswer",
};

/** Şıkkı durumuna göre renklendirir ve seçilince bildirir. */
export default function AnswerOption({ option, status, disabled, onSelect }: AnswerOptionProps) {
  const { t } = useTranslation("test");
  const badgeKey = BADGE_KEYS[status];

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={`flex w-full items-center justify-between rounded-xl border p-4 text-left transition-colors disabled:cursor-default ${BORDER_CLASSES[status]}`}
    >
      <div className="flex items-center gap-3">
        <OptionBubble label={option.label} status={status} />
        <div className="space-y-1 text-sm">
          {option.blocks.map((block, blockIndex) => (
            <Markdown key={blockIndex} content={block.md} />
          ))}
        </div>
      </div>
      {badgeKey && (
        <span className={`text-xs font-semibold ${BADGE_COLORS[status]}`}>{t(badgeKey)}</span>
      )}
    </button>
  );
}
