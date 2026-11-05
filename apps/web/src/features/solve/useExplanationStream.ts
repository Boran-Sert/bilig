/**
 * Yanlış cevap anlatımı için SSE akışını yönetir ve alıntı bloklarını toplar.
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

interface StreamState {
  text: string;
  citationBlockIds: number[];
  isStreaming: boolean;
  isDone: boolean;
  error: string | null;
}

/**
 * Anlatım akışı olaylarını dinler, metin parçalarını ve alıntıları biriktirir.
 */
export function useExplanationStream() {
  const [state, setState] = useState<StreamState>({
    text: "",
    citationBlockIds: [],
    isStreaming: false,
    isDone: false,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  /** Akışı sıfırlar. */
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setState({
      text: "",
      citationBlockIds: [],
      isStreaming: false,
      isDone: false,
      error: null,
    });
  }, []);

  /** Anlatım akışını başlatır. */
  const startExplanation = useCallback(async (sessionId: number, questionId: number) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setState({
      text: "",
      citationBlockIds: [],
      isStreaming: true,
      isDone: false,
      error: null,
    });

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

      if (!response.ok || !response.body) {
        setState((previous) => ({
          ...previous,
          isStreaming: false,
          error: i18n.t("solve.explanationFailed", { ns: "test" }),
        }));
        return;
      }

      const reader = response.body.getReader();
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
            handleEvent(currentEvent, rawData);
          }
        }
      }

      setState((previous) => ({ ...previous, isStreaming: false, isDone: true }));
    } catch {
      if (controller.signal.aborted) {
        return;
      }
      setState((previous) => ({
        ...previous,
        isStreaming: false,
        error: i18n.t("solve.explanationFailed", { ns: "test" }),
      }));
    }

    /** SSE olayına göre durumu günceller. */
    function handleEvent(eventName: string, dataString: string) {
      let parsed;
      try {
        parsed = JSON.parse(dataString);
      } catch {
        setState((previous) => ({
          ...previous,
          error: i18n.t("solve.explanationFailed", { ns: "test" }),
        }));
        return;
      }
      if (eventName === "delta" && typeof parsed.text === "string") {
        setState((previous) => ({ ...previous, text: previous.text + parsed.text }));
      } else if (eventName === "citation" && typeof parsed.blockId === "number") {
        setState((previous) => ({
          ...previous,
          citationBlockIds: previous.citationBlockIds.includes(parsed.blockId)
            ? previous.citationBlockIds
            : [...previous.citationBlockIds, parsed.blockId],
        }));
      } else if (eventName === "error") {
        setState((previous) => ({ ...previous, error: getProblemMessage(parsed) }));
      }
    }
  }, []);

  return {
    ...state,
    startExplanation,
    reset,
  };
}
