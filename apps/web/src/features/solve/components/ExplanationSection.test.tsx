/**
 * ExplanationSection bileşeninin canlı anlatım metni ve alıntı kartları sunumunu test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import ExplanationSection from "./ExplanationSection";

const { useExplanationStreamMock, startExplanationMock } = vi.hoisted(() => ({
  useExplanationStreamMock: vi.fn(),
  startExplanationMock: vi.fn(),
}));

vi.mock("../useExplanationStream", () => ({
  useExplanationStream: useExplanationStreamMock,
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
    useExplanationStreamMock.mockReturnValue({
      text: "Eylül psikolojik bir romandır.",
      citationBlockIds: [12, 15],
      isStreaming: false,
      isDone: true,
      error: null,
      startExplanation: startExplanationMock,
    });
  });

  test("başlığı, anlatım metnini ve alıntı kartlarını gösterir", () => {
    render(<ExplanationSection sessionId={1} questionId={5} />);

    expect(screen.getByRole("heading", { name: "Neden yanlış?" })).toBeInTheDocument();
    expect(screen.getByText("Eylül psikolojik bir romandır.")).toBeInTheDocument();
    expect(screen.getByTestId("citation-12")).toBeInTheDocument();
    expect(screen.getByTestId("citation-15")).toBeInTheDocument();
    expect(startExplanationMock).toHaveBeenCalledWith(1, 5);
  });

  test("hata durumunda hata uyarısını gösterir", () => {
    useExplanationStreamMock.mockReturnValue({
      text: "",
      citationBlockIds: [],
      isStreaming: false,
      isDone: false,
      error: "Anlatım akışı başarısız oldu.",
      startExplanation: startExplanationMock,
    });

    render(<ExplanationSection sessionId={1} questionId={5} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Anlatım akışı başarısız oldu.");
  });
});
