/**
 * Sohbet girdi alanını ve "Başka örnekle anlat" düğmesini sunar.
 */
import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";

interface ChatInputBarProps {
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
  isLimitReached: boolean;
}

/**
 * Öğrencinin soru sormasını sağlar; limit dolunca girdiyi kilitler.
 */
export default function ChatInputBar({
  onSendMessage,
  isStreaming,
  isLimitReached,
}: ChatInputBarProps) {
  const { t } = useTranslation("test");
  const [inputText, setInputText] = useState("");

  /** Metin gönderimini tetikler. */
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isStreaming || isLimitReached) {
      return;
    }
    onSendMessage(trimmed);
    setInputText("");
  }

  /** Hızlı eylemle başka örnek talep eder. */
  function handleAnotherExample() {
    if (isStreaming || isLimitReached) {
      return;
    }
    onSendMessage(t("solve.anotherExamplePrompt"));
  }

  return (
    <div className="space-y-2 border-t border-border/80 pt-3">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            placeholder={
              isLimitReached ? t("solve.dailyLimitReached") : t("solve.chatInputPlaceholder")
            }
            disabled={isStreaming || isLimitReached}
            className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!inputText.trim() || isStreaming || isLimitReached}
          >
            {t("solve.send")}
          </Button>
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAnotherExample}
            disabled={isStreaming || isLimitReached}
            className="h-7 text-xs"
          >
            {t("solve.anotherExample")}
          </Button>
        </div>
      </form>
    </div>
  );
}
