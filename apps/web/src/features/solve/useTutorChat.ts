/**
 * Yanlış cevap anlatımı ve karşılıklı sohbet akışını SSE ile yönetir.
 */
import { useCallback, useRef, useState } from "react";
import { DAILY_CHAT_LIMIT } from "../../lib/constants";

/** Çerezin değerini okur. */
function getCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  citationBlockIds: number[];
  isStreaming?: boolean;
}

/** Bugünün mesaj sayacını yerel depolamadan okur. */
function getStoredDailyCount(): number {
  try {
    const today = new Date().toISOString().slice(0, 10);
    const value = localStorage.getItem(`tutor_chat_count_${today}`);
    return value ? parseInt(value, 10) || 0 : 0;
  } catch {
    return 0;
  }
}

/** Bugünün mesaj sayacını yerel depolamaya yazar. */
function setStoredDailyCount(count: number) {
  try {
    const today = new Date().toISOString().slice(0, 10);
    localStorage.setItem(`tutor_chat_count_${today}`, String(count));
  } catch {
    // Hata yoksayılır
  }
}

/**
 * Anlatım ve sohbet SSE akışını dinler; mesajları ve limiti yönetir.
 */
export function useTutorChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dailyUsedCount, setDailyUsedCount] = useState<number>(getStoredDailyCount);

  const abortControllerRef = useRef<AbortController | null>(null);

  /** SSE gövdesini satır satır okur ve olayları dağıtır. */
  async function consumeSseStream(
    response: Response,
    assistantMessageId: string,
    onDone?: (convId?: number) => void,
  ) {
    const reader = response.body?.getReader();
    if (!reader) {
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      let currentEvent = "message";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = "message";
          continue;
        }
        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith("data:")) {
          const rawData = trimmed.slice(5).trim();
          handleSseEvent(currentEvent, rawData, assistantMessageId, onDone);
        }
      }
    }
  }

  /** Tekil SSE olayını işler. */
  function handleSseEvent(
    event: string,
    data: string,
    assistantId: string,
    onDone?: (convId?: number) => void,
  ) {
    try {
      const parsed = JSON.parse(data);
      if (event === "delta" && typeof parsed.text === "string") {
        setMessages((previous) =>
          previous.map((msg) =>
            msg.id === assistantId ? { ...msg, text: msg.text + parsed.text } : msg,
          ),
        );
      } else if (event === "citation" && typeof parsed.blockId === "number") {
        setMessages((previous) =>
          previous.map((msg) =>
            msg.id === assistantId && !msg.citationBlockIds.includes(parsed.blockId)
              ? { ...msg, citationBlockIds: [...msg.citationBlockIds, parsed.blockId] }
              : msg,
          ),
        );
      } else if (event === "done") {
        setMessages((previous) =>
          previous.map((msg) => (msg.id === assistantId ? { ...msg, isStreaming: false } : msg)),
        );
        onDone?.(parsed.conversationId);
      } else if (event === "error") {
        setError(parsed.detail ?? parsed.title ?? "Hata oluştu.");
      }
    } catch {
      // Hatalı JSON yoksayılır
    }
  }

  /** İlk yanlış cevap anlatımını başlatır. */
  const startExplanation = useCallback(async (sessionId: number, questionId: number) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const explanationId = `explanation-${questionId}`;
    setMessages([
      { id: explanationId, role: "assistant", text: "", citationBlockIds: [], isStreaming: true },
    ]);
    setIsStreaming(true);
    setError(null);

    try {
      const xsrf = getCookie("XSRF-TOKEN");
      const response = await fetch("/api/tutor/explanations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(xsrf ? { "X-XSRF-TOKEN": xsrf } : {}),
        },
        credentials: "include",
        body: JSON.stringify({ sessionId, questionId }),
        signal: controller.signal,
      });

      if (!response.ok) {
        setError("Anlatım akışı başlatılamadı.");
        setIsStreaming(false);
        return;
      }

      await consumeSseStream(response, explanationId, (newConvId) => {
        if (newConvId) {
          setConversationId(newConvId);
        }
      });
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Bağlantı hatası.");
      }
    } finally {
      setIsStreaming(false);
    }
  }, []);

  /** Öğrencinin yeni sohbet mesajını gönderir. */
  const sendMessage = useCallback(
    async (text: string) => {
      const trimmedText = text.trim();
      if (!trimmedText || !conversationId || isStreaming || dailyUsedCount >= DAILY_CHAT_LIMIT) {
        return;
      }

      const userMessageId = `user-${Date.now()}`;
      const assistantMessageId = `assistant-${Date.now()}`;

      setMessages((previous) => [
        ...previous,
        { id: userMessageId, role: "user", text: trimmedText, citationBlockIds: [] },
        {
          id: assistantMessageId,
          role: "assistant",
          text: "",
          citationBlockIds: [],
          isStreaming: true,
        },
      ]);

      const newDailyCount = dailyUsedCount + 1;
      setDailyUsedCount(newDailyCount);
      setStoredDailyCount(newDailyCount);
      setIsStreaming(true);
      setError(null);

      try {
        const xsrf = getCookie("XSRF-TOKEN");
        const response = await fetch(`/api/tutor/conversations/${conversationId}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(xsrf ? { "X-XSRF-TOKEN": xsrf } : {}),
          },
          credentials: "include",
          body: JSON.stringify({ text: trimmedText }),
        });

        if (!response.ok) {
          setError(
            response.status === 429 ? "Günlük mesaj limitine ulaşıldı." : "Mesaj gönderilemedi.",
          );
          setIsStreaming(false);
          return;
        }

        await consumeSseStream(response, assistantMessageId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Bağlantı hatası.");
      } finally {
        setIsStreaming(false);
      }
    },
    [conversationId, isStreaming, dailyUsedCount],
  );

  return {
    messages,
    conversationId,
    isStreaming,
    error,
    dailyUsedCount,
    dailyLimit: DAILY_CHAT_LIMIT,
    isLimitReached: dailyUsedCount >= DAILY_CHAT_LIMIT,
    startExplanation,
    sendMessage,
  };
}
