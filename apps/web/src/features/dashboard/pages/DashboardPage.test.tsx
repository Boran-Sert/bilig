/**
 * DashboardPage sayfasının özet, test, kazanım ve hata türü dağılımını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import DashboardPage from "./DashboardPage";

const { useMeMock, useDashboardMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
  useDashboardMock: vi.fn(),
}));

vi.mock("../../auth/api", () => ({
  useMe: useMeMock,
}));

vi.mock("../api", () => ({
  useDashboard: useDashboardMock,
}));

afterEach(cleanup);

describe("DashboardPage", () => {
  beforeEach(() => {
    useMeMock.mockReturnValue({
      data: { id: 1, displayName: "Elif", grade: 12 },
    });
  });

  const mockDashboardData = {
    summary: {
      answeredQuestionCount: 312,
      accuracyPercent: 64,
      latestNet: 15.25,
      latestQuestionCount: 24,
    },
    activeSessions: [
      {
        sessionId: 10,
        examId: 101,
        examTitle: "Roman · Kazanım Testi 3",
        questionCount: 12,
        answeredCount: 4,
        currentPosition: 5,
      },
    ],
    failedOutcomes: [
      {
        code: "A.2.15",
        title: "Türün yazar ve eserleri",
        totalWrongCount: 3,
        testTitle: "Roman Testi 3",
        testWrongCount: 3,
      },
    ],
    unitAccuracy: [
      {
        unitTitle: "Roman",
        answeredCount: 50,
        correctCount: 26,
        accuracyPercent: 52,
      },
    ],
    errorTypeDistribution: [
      { errorType: "KNOWLEDGE", answerCount: 46 },
      { errorType: "MISCONCEPTION", answerCount: 21 },
      { errorType: "ATTENTION", answerCount: 18 },
      { errorType: "READING", answerCount: 15 },
    ],
  };

  test("öğrenci karşılama başlığını ve sınıfını gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: mockDashboardData,
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Merhaba Elif")).toBeInTheDocument();
    expect(
      screen.getByText("Genel ilerleme özetin ve kaldığın yerden devam edebileceğin testler."),
    ).toBeInTheDocument();
  });

  test("özet metrikleri (soru, doğruluk, son net) doğru gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: mockDashboardData,
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("312")).toBeInTheDocument();
    expect(screen.getByText("%64")).toBeInTheDocument();
    expect(screen.getByText("15.25")).toBeInTheDocument();
    expect(screen.getByText(/24 soruda/)).toBeInTheDocument();
  });

  test("devam eden testleri ve devam et bağlantısını gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: mockDashboardData,
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Roman · Kazanım Testi 3")).toBeInTheDocument();
    const resumeLink = screen.getByRole("link", { name: "Devam et" });
    expect(resumeLink).toHaveAttribute("href", "/tests/101/solve");
  });

  test("başarısız kazanımları ve pratik yap butonunu gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: mockDashboardData,
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("A.2.15")).toBeInTheDocument();
    expect(screen.getByText("Türün yazar ve eserleri")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Pratik yap" })).toHaveAttribute("href", "/tests");
  });

  test("tür başarı çubuklarını ve hata türü dağılımını gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: mockDashboardData,
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Roman")).toBeInTheDocument();
    expect(screen.getByText("%52")).toBeInTheDocument();

    expect(screen.getByText("Bilgi eksikliği")).toBeInTheDocument();
    expect(screen.getByText("Kavram yanılgısı")).toBeInTheDocument();
    expect(screen.getByText("Dikkat")).toBeInTheDocument();
    expect(screen.getByText("Okuma")).toBeInTheDocument();
  });

  test("yüklenme durumunda yükleniyor metnini gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: null,
      isPending: true,
      isError: false,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Öğrenci paneli yükleniyor...")).toBeInTheDocument();
  });

  test("sunucu hatasında hata mesajını gösterir", () => {
    useDashboardMock.mockReturnValue({
      data: null,
      isPending: false,
      isError: true,
      error: new ApiError({ code: "INTERNAL_ERROR", detail: "Sunucuya ulaşılamadı" }, 500),
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Sunucuya ulaşılamadı");
  });
});
