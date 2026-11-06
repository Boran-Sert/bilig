/**
 * Yanlış cevabın akışla gelen anlatımını ve karşılıklı sohbet ekranını sunar.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useTutorChat } from "../useTutorChat";
import ChatInputBar from "./ChatInputBar";
import ChatMessageBubble from "./ChatMessageBubble";
import ChatPanelShell from "./ChatPanelShell";

interface ExplanationSectionProps {
  sessionId: number;
  questionId: number;
}

/**
 * Anlatım akışını başlatır, sohbet mesajlarını ve girdi alanını çizer.
 */
export default function ExplanationSection({ sessionId, questionId }: ExplanationSectionProps) {
  const { t } = useTranslation("test");
  const { messages, isStreaming, error, isLimitReached, startExplanation, sendMessage } =
    useTutorChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    startExplanation(sessionId, questionId);
  }, [sessionId, questionId, startExplanation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ChatPanelShell
      title={t("solve.whyWrong")}
      note={t("solve.styleLabel")}
      ariaLabel={t("solve.whyWrong")}
      footer={
        <ChatInputBar
          onSendMessage={sendMessage}
          isStreaming={isStreaming}
          isLimitReached={isLimitReached}
        />
      }
    >
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}

      {error && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-xs text-destructive">
          {error}
        </p>
      )}

      <div ref={messagesEndRef} />
    </ChatPanelShell>
  );
}
