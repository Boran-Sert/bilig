/**
 * ReviewItemCard bileşeninin soru, paragraf ve kaynak ayrımını ve karar aksiyonlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import type { ReviewItemResponse } from "../types";
import ReviewItemCard from "./ReviewItemCard";

vi.mock("../api", () => ({
  /** Düzeltme modalı için kazanım listesi hook'unu taklit eder. */
  useOutcomes: () => ({
    data: [{ id: 10, code: "A.1.1", title: "Metin tahlili" }],
  }),
}));

afterEach(cleanup);

describe("ReviewItemCard", () => {
  const onApprove = vi.fn();
  const onReject = vi.fn();
  const onFix = vi.fn();
  const onOpenPage = vi.fn();

  beforeEach(() => {
    onApprove.mockReset();
    onReject.mockReset();
    onFix.mockReset();
    onOpenPage.mockReset();
  });

  const questionItem: ReviewItemResponse = {
    id: 1,
    targetType: "QUESTION",
    targetId: 101,
    reason: "LOW_CONFIDENCE",
    questionContent: { stem: [{ md: "Aşağıdakilerden hangisi bir kasidedir?" }] },
    blockMarkdown: null,
    sourceTitle: null,
    pageId: 50,
    pageNo: 12,
    outcomes: [{ id: 10, code: "A.1.1", title: "Metin tahlili", mappedBy: "AI" }],
    problems: [],
    createdAt: "2026-11-05T00:00:00Z",
  };

  const sourceItem: ReviewItemResponse = {
    id: 2,
    targetType: "SOURCE",
    targetId: 202,
    reason: "VALIDATION_FAILED",
    questionContent: null,
    blockMarkdown: null,
    sourceTitle: "12. Sınıf Soru Bankası",
    pageId: null,
    pageNo: null,
    outcomes: [],
    problems: [{ code: "OPTION_COUNT", pageNo: 15, pageId: 55, test: 3, number: 4 }],
    createdAt: "2026-11-05T00:00:00Z",
  };

  test("soru kaydında Onayla, Düzelt ve Reddet butonlarını gösterir", () => {
    render(
      <ReviewItemCard
        item={questionItem}
        onApprove={onApprove}
        onReject={onReject}
        onFix={onFix}
        onOpenPage={onOpenPage}
      />,
    );

    expect(screen.getByText("Soru")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onayla" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Düzelt" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reddet" })).toBeInTheDocument();
  });

  test("kaynak kaydında Düzelt butonu gösterilmez (Kritik Kabul Kriteri)", () => {
    render(
      <ReviewItemCard
        item={sourceItem}
        onApprove={onApprove}
        onReject={onReject}
        onFix={onFix}
        onOpenPage={onOpenPage}
      />,
    );

    expect(screen.getByText("12. Sınıf Soru Bankası")).toBeInTheDocument();
    expect(screen.getByText("Şık sayısı 5 değil")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onayla" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reddet" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Düzelt" })).not.toBeInTheDocument();
  });

  test("Onayla ve Reddet butonlarına tıklandığında ilgili fonksiyonları çağırır", () => {
    render(
      <ReviewItemCard
        item={questionItem}
        onApprove={onApprove}
        onReject={onReject}
        onFix={onFix}
        onOpenPage={onOpenPage}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Onayla" }));
    expect(onApprove).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByRole("button", { name: "Reddet" }));
    expect(onReject).toHaveBeenCalledWith(1);
  });

  test("Sayfayı aç butonuna tıklandığında onOpenPage fonksiyonunu çağırır", () => {
    render(
      <ReviewItemCard
        item={sourceItem}
        onApprove={onApprove}
        onReject={onReject}
        onFix={onFix}
        onOpenPage={onOpenPage}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Sayfayı aç" }));
    expect(onOpenPage).toHaveBeenCalledWith(55);
  });

  test("Düzelt butonuna tıklanıp kazanım kaydedildiğinde onFix çağrılır", () => {
    render(
      <ReviewItemCard
        item={questionItem}
        onApprove={onApprove}
        onReject={onReject}
        onFix={onFix}
        onOpenPage={onOpenPage}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Düzelt" }));
    expect(screen.getByText("Kazanımları Düzenle")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Kazanımları Kaydet ve Yayına Al" }));
    expect(onFix).toHaveBeenCalledWith(1, [10]);
  });
});
