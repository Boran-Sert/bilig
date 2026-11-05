/**
 * Sohbet hook'unun SSE olaylarını okumasını, hata sonrası durumunu ve sunucu limitini test eder.
 * @vitest-environment jsdom
 */
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useTutorChat } from "./useTutorChat";

/** Verilen parçaları sırayla akıtan bir fetch yanıtı üretir. */
function streamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
  return new Response(body, { status: 200 });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("useTutorChat", () => {
  test("keeps the event name when its data line arrives in the next chunk", async () => {
    const chunks = ["event:delta\n", 'data:{"text":"Merhaba"}\n\n', "event:citation\n"];
    chunks.push('data:{"blockId":7}\n\n', 'event:done\ndata:{"conversationId":3}\n\n');
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamResponse(chunks)));
    const { result } = renderHook(() => useTutorChat());

    await act(() => result.current.startExplanation(1, 5));

    expect(result.current.messages[0]).toMatchObject({
      text: "Merhaba",
      citationBlockIds: [7],
      isStreaming: false,
    });
    expect(result.current.conversationId).toBe(3);
  });

  test("stops the waiting indicator when the stream ends with an error", async () => {
    const chunks = ['event:error\ndata:{"code":"AI_UNAVAILABLE"}\n\n'];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamResponse(chunks)));
    const { result } = renderHook(() => useTutorChat());

    await act(() => result.current.startExplanation(1, 5));

    expect(result.current.error).not.toBeNull();
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[0].isStreaming).toBe(false);
  });

  test("locks the chat when the server reports the daily limit", async () => {
    const done = 'event:done\ndata:{"conversationId":3}\n\n';
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(streamResponse([done]))
      .mockResolvedValueOnce(new Response(null, { status: 429 }));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useTutorChat());
    await act(() => result.current.startExplanation(1, 5));

    await act(() => result.current.sendMessage("Neden?"));

    await waitFor(() => expect(result.current.isLimitReached).toBe(true));
    expect(result.current.messages.every((message) => !message.isStreaming)).toBe(true);
  });
});
