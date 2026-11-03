/**
 * SolvePage bileşeninin kaldığı sorudan başlama, cevap gönderme ve kazanım gösterimini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import SolvePage from "./SolvePage";

const { useStartSessionMock, useSubmitAnswerMock, startMutateMock, submitMutateMock } = vi.hoisted(
  () => ({
    useStartSessionMock: vi.fn(),
    useSubmitAnswerMock: vi.fn(),
    startMutateMock: vi.fn(),
    submitMutateMock: vi.fn(),
  }),
);

vi.mock("../api", () => ({
  useStartSession: useStartSessionMock,
  useSubmitAnswer: useSubmitAnswerMock,
}));

const mockQuestions = [
  {
    id: 10,
    position: 1,
    selectedOption: null,
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
    content: {
      passage: [{ type: "paragraph", md: "Roman parçası" }],
      stem: [{ type: "paragraph", md: "İkinci soru kökü" }],
      options: [
        { label: "A", blocks: [{ type: "paragraph", md: "Eylül" }] },
        { label: "B", blocks: [{ type: "paragraph", md: "Küçük Ağa" }] },
      ],
    },
  },
];

/** Çözme sayfasını belirli rota ve test ID ile oluşturur. */
function renderSolvePage(initialPosition = 1) {
  startMutateMock.mockImplementation((_id, options) => {
    options?.onSuccess?.({
      sessionId: 99,
      currentPosition: initialPosition,
      questions: mockQuestions,
    });
  });

  return render(
    <MemoryRouter initialEntries={["/tests/1/solve"]}>
      <Routes>
        <Route path="/tests/:testId/solve" element={<SolvePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("SolvePage", () => {
  beforeEach(() => {
    startMutateMock.mockReset();
    submitMutateMock.mockReset();

    useStartSessionMock.mockReturnValue({
      mutate: startMutateMock,
      isPending: false,
      isError: false,
      data: {
        sessionId: 99,
        currentPosition: 1,
        questions: mockQuestions,
      },
      error: null,
    });

    useSubmitAnswerMock.mockReturnValue({
      mutate: submitMutateMock,
      reset: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    });
  });

  test("sayfa yenilendiğinde oturumun kaldığı sorudan açılır (Kabul Kriteri 2)", () => {
    // 2. sorudan başlamasını simüle eder
    useStartSessionMock.mockReturnValue({
      mutate: startMutateMock,
      isPending: false,
      isError: false,
      data: {
        sessionId: 99,
        currentPosition: 2,
        questions: mockQuestions,
      },
      error: null,
    });

    renderSolvePage(2);

    expect(screen.getByText("İkinci soru kökü")).toBeInTheDocument();
    expect(screen.getByText("Roman parçası")).toBeInTheDocument();
    expect(screen.getByText("Soru 2 / 2")).toBeInTheDocument();
  });

  test("yanlış cevap verildiğinde doğru şıkkı ve kazanımları gösterir (Kabul Kriteri 1)", async () => {
    submitMutateMock.mockImplementation((_params, options) => {
      options?.onSuccess?.({
        isCorrect: false,
        correctOption: "B",
        outcomes: [
          { code: "A.2.15", title: "Türün yazar ve eserleri" },
          { code: "A.2.3", title: "Tema ve konu" },
        ],
      });
    });

    renderSolvePage(1);

    // Öğrenci yanlış olan A şıkkına tıklar
    const optionA = screen.getByText("A şıkkı").closest("button")!;
    fireEvent.click(optionA);

    await waitFor(() => {
      expect(screen.getByText("Senin cevabın")).toBeInTheDocument();
    });
    expect(screen.getByText("Doğru cevap")).toBeInTheDocument();

    // Kazanımların listelendiğini doğrular
    expect(screen.getByText("Bu sorunun kazanımları:")).toBeInTheDocument();
    expect(screen.getByText(/A\.2\.15 Türün yazar ve eserleri/)).toBeInTheDocument();
    expect(screen.getByText(/A\.2\.3 Tema ve konu/)).toBeInTheDocument();
  });

  test("sonraki ve önceki butonlarıyla sorular arasında gezilebilir", () => {
    renderSolvePage(1);

    expect(screen.getByText("Birinci soru kökü")).toBeInTheDocument();

    // Sonraki düğmesine tıklar
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    expect(screen.getByText("İkinci soru kökü")).toBeInTheDocument();

    // Önceki düğmesine tıklar
    fireEvent.click(screen.getByRole("button", { name: "Önceki" }));
    expect(screen.getByText("Birinci soru kökü")).toBeInTheDocument();
  });

  test("yenilemeden önce cevaplanan soruda seçilen şıkkı işaretler ve kilitler", () => {
    const answeredQuestions = [{ ...mockQuestions[0], selectedOption: "B" }, mockQuestions[1]];
    useStartSessionMock.mockReturnValue({
      mutate: startMutateMock,
      isPending: false,
      isError: false,
      data: { sessionId: 99, currentPosition: 1, questions: answeredQuestions },
      error: null,
    });

    renderSolvePage(1);

    const optionB = screen.getByText("B şıkkı").closest("button")!;
    expect(optionB).toHaveTextContent("Senin cevabın");
    expect(optionB).toBeDisabled();
    expect(screen.getByText("A şıkkı").closest("button")).toBeDisabled();
    expect(
      screen.getByText("%50 tamamlandı · kaldığın yerden devam ediyorsun"),
    ).toBeInTheDocument();
  });

  test("cevap kaydedilemezse sunucunun mesajını gösterir", () => {
    useSubmitAnswerMock.mockReturnValue({
      mutate: submitMutateMock,
      reset: vi.fn(),
      isPending: false,
      isError: true,
      error: new ApiError(
        { code: "ANSWER_ALREADY_SUBMITTED", detail: "Bu soru zaten cevaplandı." },
        409,
      ),
    });

    renderSolvePage(1);

    expect(screen.getByRole("alert")).toHaveTextContent("Bu soru zaten cevaplandı.");
  });
});
