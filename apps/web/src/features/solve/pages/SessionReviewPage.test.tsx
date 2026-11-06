/**
 * SessionReviewPage bileşeninin doğru şık gösterimini, boş soruyu ve anlatım açılışını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import SessionReviewPage from "./SessionReviewPage";

const { useSessionReviewMock } = vi.hoisted(() => ({ useSessionReviewMock: vi.fn() }));

vi.mock("../api", () => ({ useSessionReview: useSessionReviewMock }));

vi.mock("../components/ExplanationSection", () => ({
  /** Test için anlatım bölümü sahte bileşenini sunar. */
  default: ({ questionId }: { questionId: number }) => (
    <div data-testid="explanation-section">Anlatım {questionId}</div>
  ),
}));

const reviewQuestions = [
  {
    id: 10,
    position: 1,
    selectedOption: "A",
    correctOption: "B",
    isCorrect: false,
    outcomes: [{ code: "K-1", title: "Örnek kazanım" }],
    content: {
      passage: null,
      stem: [{ type: "paragraph", md: "Birinci soru kökü" }],
      options: [
        { label: "A", blocks: [{ type: "paragraph", md: "A şıkkı" }] },
        { label: "B", blocks: [{ type: "paragraph", md: "B şıkkı" }] },
      ],
    },
  },
  {
    id: 20,
    position: 2,
    selectedOption: null,
    correctOption: "A",
    isCorrect: null,
    outcomes: [],
    content: {
      passage: null,
      stem: [{ type: "paragraph", md: "İkinci soru kökü" }],
      options: [
        { label: "A", blocks: [{ type: "paragraph", md: "A şıkkı" }] },
        { label: "B", blocks: [{ type: "paragraph", md: "B şıkkı" }] },
      ],
    },
  },
];

/** İnceleme sayfasını oturum numarasıyla ve verilen sunucu cevabıyla çizer. */
function renderReview(state: Record<string, unknown>) {
  useSessionReviewMock.mockReturnValue({ isPending: false, isError: false, ...state });
  return render(
    <MemoryRouter initialEntries={["/sessions/99/review"]}>
      <Routes>
        <Route path="/sessions/:sessionId/review" element={<SessionReviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("SessionReviewPage", () => {
  test("yanlış soruda seçilen ve doğru şıkkı işaretler, anlatımı açabilir", () => {
    renderReview({ data: { questions: reviewQuestions } });

    expect(screen.getByText("Soru 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("A şıkkı").closest("button")).toHaveTextContent("Senin cevabın");
    expect(screen.getByText("B şıkkı").closest("button")).toHaveTextContent("Doğru cevap");
    expect(screen.queryByTestId("explanation-section")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Neden yanlış?" }));

    expect(screen.getByTestId("explanation-section")).toHaveTextContent("Anlatım 10");
  });

  test("boş bırakılan soruda doğru şıkkı gösterir ve anlatımı kapalı tutar", () => {
    renderReview({ data: { questions: reviewQuestions } });

    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));

    expect(screen.getByText("İkinci soru kökü")).toBeInTheDocument();
    expect(screen.getByText("Bu soruyu boş bıraktın.")).toBeInTheDocument();
    expect(screen.getByText("A şıkkı").closest("button")).toHaveTextContent("Doğru cevap");
    expect(screen.getByRole("button", { name: "Neden yanlış?" })).toBeDisabled();
    expect(screen.getAllByRole("link", { name: "Sonuca dön" })).toHaveLength(2);
  });

  test("inceleme alınamazsa sunucu mesajını ve sonuca dönüş bağlantısını gösterir", () => {
    renderReview({
      isError: true,
      error: { message: "Oturum henüz tamamlanmadı." },
      data: undefined,
    });

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sonuca dön" })).toHaveAttribute(
      "href",
      "/sessions/99/result",
    );
  });
});
