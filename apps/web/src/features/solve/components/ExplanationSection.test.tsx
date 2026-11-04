/**
 * ExplanationSection bileşeninin canlı anlatım ve sohbet listesi sunumunu test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import ExplanationSection from "./ExplanationSection";

const { useTutorChatMock, startExplanationMock, sendMessageMock } = vi.hoisted(() => ({
  useTutorChatMock: vi.fn(),
  startExplanationMock: vi.fn(),
  sendMessageMock: vi.fn(),
}));

vi.mock("../useTutorChat", () => ({
  useTutorChat: useTutorChatMock,
}));

vi.mock("./CitationCard", () => ({
  /** Test için alıntı kartı sahte bileşenini sunar. */
  default: ({ blockId }: { blockId: number }) => (
    <div data-testid={`citation-${blockId}`}>Alıntı {blockId}</div>
  ),
}));

afterEach(cleanup);

describe("ExplanationSection", () => {
  beforeEach(() => {
    startExplanationMock.mockReset();
    sendMessageMock.mockReset();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();

    useTutorChatMock.mockReturnValue({
      messages: [
        {
          id: "exp-1",
          role: "assistant",
          text: "Eylül psikolojik bir romandır.",
          citationBlockIds: [12],
          isStreaming: false,
        },
        {
          id: "user-1",
          role: "user",
          text: "Devlet Ana da öyle mi?",
          citationBlockIds: [],
        },
      ],
      conversationId: 99,
      isStreaming: false,
      error: null,
      dailyUsedCount: 12,
      dailyLimit: 30,
      isLimitReached: false,
      startExplanation: startExplanationMock,
      sendMessage: sendMessageMock,
    });
  });

  test("başlığı, mesajları, alıntıları ve günlük limiti gösterir", () => {
    render(<ExplanationSection sessionId={1} questionId={5} />);

    expect(screen.getByRole("heading", { name: "Neden yanlış?" })).toBeInTheDocument();
    expect(screen.getByText("Eylül psikolojik bir romandır.")).toBeInTheDocument();
    expect(screen.getByText("Devlet Ana da öyle mi?")).toBeInTheDocument();
    expect(screen.getByTestId("citation-12")).toBeInTheDocument();
    expect(screen.getByText("Bugün 12 / 30 mesaj")).toBeInTheDocument();
    expect(startExplanationMock).toHaveBeenCalledWith(1, 5);
  });

  test("hata durumunda hata uyarısını gösterir", () => {
    useTutorChatMock.mockReturnValue({
      messages: [],
      conversationId: null,
      isStreaming: false,
      error: "Anlatım akışı başarısız oldu.",
      dailyUsedCount: 0,
      dailyLimit: 30,
      isLimitReached: false,
      startExplanation: startExplanationMock,
      sendMessage: sendMessageMock,
    });

    render(<ExplanationSection sessionId={1} questionId={5} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Anlatım akışı başarısız oldu.");
  });
});
