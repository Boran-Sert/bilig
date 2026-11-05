/**
 * Yanlış cevap anlatımı ve karşılıklı sohbet akışını SSE ile yönetir.
 */
import { useCallback, useRef, useState } from "react";
import { getProblemMessage } from "../../lib/api/problem";
import i18n from "../../lib/i18n";

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

/**
 * Anlatım ve sohbet SSE akışını dinler; mesajları ve sunucunun bildirdiği limiti yönetir.
 */
export function useTutorChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLimitReached, setIsLimitReached] = useState(false);

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
    let currentEvent = "message";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

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
    let parsed;
    try {
      parsed = JSON.parse(data);
    } catch {
      setError(i18n.t("solve.explanationFailed", { ns: "test" }));
      return;
    }
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
      setIsLimitReached(parsed.code === "DAILY_LIMIT_REACHED");
      setError(getProblemMessage(parsed));
    }
  }

  /** Asistan mesajının bekleme göstergesini kapatır. */
  function stopStreaming(assistantId: string) {
    setIsStreaming(false);
    setMessages((previous) =>
      previous.map((msg) => (msg.id === assistantId ? { ...msg, isStreaming: false } : msg)),
    );
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
        setError(i18n.t("solve.explanationFailed", { ns: "test" }));
        return;
      }

      await consumeSseStream(response, explanationId, (newConvId) => {
        if (newConvId) {
          setConversationId(newConvId);
        }
      });
    } catch {
      if (!controller.signal.aborted) {
        setError(i18n.t("solve.explanationFailed", { ns: "test" }));
      }
    } finally {
      if (!controller.signal.aborted) {
        stopStreaming(explanationId);
      }
    }
  }, []);

  /** Öğrencinin yeni sohbet mesajını gönderir. */
  const sendMessage = useCallback(
    async (text: string) => {
      const trimmedText = text.trim();
      if (!trimmedText || !conversationId || isStreaming || isLimitReached) {
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
          const limitReached = response.status === 429;
          setIsLimitReached(limitReached);
          setError(
            i18n.t(limitReached ? "solve.dailyLimitReached" : "solve.sendFailed", { ns: "test" }),
          );
          return;
        }

        await consumeSseStream(response, assistantMessageId);
      } catch {
        setError(i18n.t("solve.sendFailed", { ns: "test" }));
      } finally {
        stopStreaming(assistantMessageId);
      }
    },
    [conversationId, isStreaming, isLimitReached],
  );

  return {
    messages,
    conversationId,
    isStreaming,
    error,
    isLimitReached,
    startExplanation,
    sendMessage,
  };
}
