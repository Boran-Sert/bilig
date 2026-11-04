/**
 * ChatMessageBubble bileşeninin kullanıcı ve asistan mesajlarını doğru çizdiğini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import ChatMessageBubble from "./ChatMessageBubble";

vi.mock("./CitationCard", () => ({
  /** Test için alıntı kartı sahte bileşenini sunar. */
  default: ({ blockId }: { blockId: number }) => (
    <div data-testid={`citation-${blockId}`}>Alıntı {blockId}</div>
  ),
}));

afterEach(cleanup);

describe("ChatMessageBubble", () => {
  test("kullanıcı mesajını sağa yaslı balon olarak gösterir", () => {
    render(
      <ChatMessageBubble
        message={{
          id: "1",
          role: "user",
          text: "Devlet Ana da tarihî roman mı?",
          citationBlockIds: [],
        }}
      />,
    );

    expect(screen.getByText("Devlet Ana da tarihî roman mı?")).toBeInTheDocument();
  });

  test("asistan mesajını metin ve alıntı kartlarıyla birlikte gösterir", () => {
    render(
      <ChatMessageBubble
        message={{
          id: "2",
          role: "assistant",
          text: "Evet, Devlet Ana tarihî romandır.",
          citationBlockIds: [42],
        }}
      />,
    );

    expect(screen.getByText("Evet, Devlet Ana tarihî romandır.")).toBeInTheDocument();
    expect(screen.getByTestId("citation-42")).toBeInTheDocument();
  });
});
