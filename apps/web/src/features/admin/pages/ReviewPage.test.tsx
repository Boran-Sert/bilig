/**
 * ReviewPage sayfasının yetki kontrolü, liste gösterimi ve karar akışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import ReviewPage from "./ReviewPage";

const { useMeMock, useReviewsMock, useDecideReviewMock, mutateMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
  useReviewsMock: vi.fn(),
  useDecideReviewMock: vi.fn(),
  mutateMock: vi.fn(),
}));

vi.mock("../../auth/api", () => ({
  useMe: useMeMock,
}));

vi.mock("../api", () => ({
  useReviews: useReviewsMock,
  useDecideReview: useDecideReviewMock,
  /** Düzeltme modalı için kazanım listesi hook'unu taklit eder. */
  useOutcomes: () => ({ data: [] }),
}));

afterEach(cleanup);

describe("ReviewPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    useDecideReviewMock.mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    });
  });

  test("içerik yöneticisi yetkisi yoksa erişim engeli uyarısı gösterir", () => {
    useMeMock.mockReturnValue({
      data: { id: 1, canManageContent: false },
      isPending: false,
    });
    useReviewsMock.mockReturnValue({ data: null, isPending: false });

    render(<ReviewPage />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "İnceleme listesine erişim yetkiniz bulunmuyor.",
    );
  });

  test("inceleme listesi boş olduğunda bilgilendirme mesajı gösterir", () => {
    useMeMock.mockReturnValue({
      data: { id: 1, canManageContent: true },
      isPending: false,
    });
    useReviewsMock.mockReturnValue({
      data: { items: [], total: 0, page: 0, size: 20 },
      isPending: false,
    });

    render(<ReviewPage />);

    expect(screen.getByText("İnceleme bekleyen kayıt bulunmuyor.")).toBeInTheDocument();
  });

  test("kayıtlar listelendiğinde Onayla butonu ile APPROVE kararı iletir", () => {
    useMeMock.mockReturnValue({
      data: { id: 1, canManageContent: true },
      isPending: false,
    });
    useReviewsMock.mockReturnValue({
      data: {
        items: [
          {
            id: 15,
            targetType: "QUESTION",
            targetId: 301,
            reason: "LOW_CONFIDENCE",
            questionContent: { stem: [{ md: "Soru metni" }] },
            blockMarkdown: null,
            sourceTitle: null,
            pageId: null,
            pageNo: null,
            outcomes: [],
            problems: [],
            createdAt: "2026-11-05T00:00:00Z",
          },
        ],
        total: 1,
        page: 0,
        size: 20,
      },
      isPending: false,
    });

    render(<ReviewPage />);

    expect(screen.getByText("1 kayıt")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Onayla" }));

    expect(mutateMock).toHaveBeenCalledWith({
      id: 15,
      request: { decision: "APPROVE" },
    });
  });

  test("karar kaydedilemezse sunucunun hatasını gösterir", () => {
    useMeMock.mockReturnValue({
      data: { id: 1, canManageContent: true },
      isPending: false,
    });
    useReviewsMock.mockReturnValue({
      data: { items: [], total: 0, page: 0, size: 20 },
      isPending: false,
      isError: false,
    });
    useDecideReviewMock.mockReturnValue({
      mutate: mutateMock,
      isPending: false,
      isError: true,
      error: { detail: "Kayıt zaten karara bağlandı." },
    });

    render(<ReviewPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("Kayıt zaten karara bağlandı.");
  });
});
