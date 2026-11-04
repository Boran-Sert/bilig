/**
 * Öğrenci veya asistan mesaj balonunu, metnini ve alıntı kartlarını gösterir.
 */
import Markdown from "../../../components/Markdown";
import type { ChatMessage } from "../useTutorChat";
import CitationCard from "./CitationCard";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

/**
 * Rolüne göre sağa (kullanıcı) veya sola (asistan) hizalı mesaj balonunu çizer.
 */
export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-xs bg-primary/15 px-4 py-2.5 text-sm text-foreground shadow-xs">
          <p className="whitespace-pre-wrap leading-relaxed">{message.text}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[95%] space-y-3 rounded-2xl rounded-tl-xs bg-muted/40 p-4 text-sm text-foreground shadow-xs">
        {message.text ? (
          <div className="leading-relaxed">
            <Markdown content={message.text} />
          </div>
        ) : null}

        {message.isStreaming && (
          <span className="inline-block h-2 w-2 rounded-full bg-primary animate-ping" />
        )}

        {message.citationBlockIds.length > 0 && (
          <div className="space-y-2.5 pt-1">
            {message.citationBlockIds.map((blockId) => (
              <CitationCard key={blockId} blockId={blockId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
