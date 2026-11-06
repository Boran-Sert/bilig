/**
 * Soru cevaplanmadan önce soru asistanını, ipucunu ve serbest yazı alanını sunar.
 */
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import type { ChatMessage } from "../useTutorChat";
import ChatInputBar from "./ChatInputBar";
import ChatMessageBubble from "./ChatMessageBubble";
import ChatPanelShell from "./ChatPanelShell";

interface HintChatPanelProps {
  messages: ChatMessage[];
  error: string | null;
  isHintPending: boolean;
  isStreaming: boolean;
  isLimitReached: boolean;
  onRequestHint: () => void;
  onSendMessage: (text: string) => void;
}

/**
 * Karşılama mesajını, sohbeti, ipucu isteme düğmesini ve yazma alanını gösterir.
 * @param props Mesajlar, hata, bekleme ve limit durumu ile eylem işlevleri.
 * @returns Cevap öncesi sohbet paneli.
 */
export default function HintChatPanel({
  messages,
  error,
  isHintPending,
  isStreaming,
  isLimitReached,
  onRequestHint,
  onSendMessage,
}: HintChatPanelProps) {
  const { t } = useTranslation("test");
  const greeting: ChatMessage = {
    id: "greeting",
    role: "assistant",
    text: t("solve.assistantGreeting"),
    citationBlockIds: [],
  };

  return (
    <ChatPanelShell
      title={t("solve.assistantTitle")}
      note={t("solve.styleLabel")}
      ariaLabel={t("solve.assistantTitle")}
      footer={
        <ChatInputBar
          onSendMessage={onSendMessage}
          isStreaming={isStreaming}
          isLimitReached={isLimitReached}
          showAnotherExample={false}
        />
      }
    >
      <ChatMessageBubble message={greeting} />
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}

      {isHintPending && <p className="text-sm text-info">{t("solve.hintLoading")}</p>}
      {error && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <Button
        type="button"
        variant="outline"
        disabled={isHintPending || isStreaming}
        onClick={onRequestHint}
        className="h-10 rounded-xl border-info/40 px-4 text-info"
      >
        {t("solve.hint")}
      </Button>
    </ChatPanelShell>
  );
}
