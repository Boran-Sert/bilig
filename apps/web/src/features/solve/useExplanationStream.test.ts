/**
 * Anlatım akışı hook'unun SSE olaylarını parça sınırlarından bağımsız okuduğunu test eder.
 * @vitest-environment jsdom
 */
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useExplanationStream } from "./useExplanationStream";

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

describe("useExplanationStream", () => {
  test("keeps the event name when its data line arrives in the next chunk", async () => {
    const chunks = ["event:delta\n", 'data:{"text":"Merhaba"}\n\n', "event:citation\n"];
    chunks.push('data:{"blockId":7}\n\n');
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamResponse(chunks)));
    const { result } = renderHook(() => useExplanationStream());

    await act(() => result.current.startExplanation(1, 5));

    await waitFor(() => expect(result.current.isDone).toBe(true));
    expect(result.current.text).toBe("Merhaba");
    expect(result.current.citationBlockIds).toEqual([7]);
  });

  test("shows an error when the stream carries invalid data", async () => {
    const chunks = ["event:delta\ndata:{bozuk\n\n"];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamResponse(chunks)));
    const { result } = renderHook(() => useExplanationStream());

    await act(() => result.current.startExplanation(1, 5));

    await waitFor(() => expect(result.current.error).not.toBeNull());
  });
});
