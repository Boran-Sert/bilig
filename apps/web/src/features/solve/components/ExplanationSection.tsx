/**
 * Yanlış cevabın akışla gelen anlatımını ve karşılıklı sohbet ekranını sunar.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useTutorChat } from "../useTutorChat";
import ChatInputBar from "./ChatInputBar";
import ChatMessageBubble from "./ChatMessageBubble";

interface ExplanationSectionProps {
  sessionId: number;
  questionId: number;
}

/**
 * Anlatım akışını başlatır, sohbet mesajlarını ve girdi alanını çizer.
 */
export default function ExplanationSection({ sessionId, questionId }: ExplanationSectionProps) {
  const { t } = useTranslation("test");
  const {
    messages,
    isStreaming,
    error,
    dailyUsedCount,
    dailyLimit,
    isLimitReached,
    startExplanation,
    sendMessage,
  } = useTutorChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    startExplanation(sessionId, questionId);
  }, [sessionId, questionId, startExplanation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <aside
      aria-label={t("solve.whyWrong")}
      className="flex flex-col space-y-4 rounded-xl border border-border bg-card p-5 shadow-xs"
    >
      <div className="flex items-center justify-between border-b border-border pb-3">
        <h2 className="text-base font-semibold tracking-tight">{t("solve.whyWrong")}</h2>
        <span className="text-xs font-medium text-muted-foreground">{t("solve.styleLabel")}</span>
      </div>

      <div className="max-h-[550px] space-y-3.5 overflow-y-auto pr-1">
        {messages.map((message) => (
          <ChatMessageBubble key={message.id} message={message} />
        ))}

        {error && (
          <p role="alert" className="rounded-md bg-destructive/10 p-3 text-xs text-destructive">
            {error}
          </p>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInputBar
        onSendMessage={sendMessage}
        isStreaming={isStreaming}
        dailyUsedCount={dailyUsedCount}
        dailyLimit={dailyLimit}
        isLimitReached={isLimitReached}
      />
    </aside>
  );
}
