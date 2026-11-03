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
  default: "border-border hover:border-muted-foreground/50",
  selected: "border-primary bg-primary/5",
  correct: "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20",
  wrong: "border-destructive bg-destructive/5",
};

const BADGE_COLORS: Record<OptionStatus, string> = {
  default: "",
  selected: "text-primary",
  correct: "text-emerald-600 dark:text-emerald-400",
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
      className={`flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors disabled:cursor-default ${BORDER_CLASSES[status]}`}
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
