/**
 * SourceList bileşeninin adım gösterimini, durum rozetlerini ve hata metnini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import type { SourceListItem } from "../types";
import SourceList from "./SourceList";

afterEach(cleanup);

describe("SourceList", () => {
  test("boş liste verildiğinde boş liste uyarısını gösterir", () => {
    render(<SourceList items={[]} answerKeys={[]} isReprocessing={false} onReprocess={vi.fn()} />);
    expect(screen.getByText("Henüz yüklenmiş bir kaynak bulunmuyor.")).toBeInTheDocument();
  });

  test("kaynak dosyasını ve adım ilerlemesini doğru render eder", () => {
    const items: SourceListItem[] = [
      {
        sourceId: 101,
        fileName: "tde12-ders-kitabi.pdf",
        kind: "TEXTBOOK",
        status: "PROCESSING",
        lastCompletedStep: "EXTRACT",
        stepIndex: 2,
        totalSteps: 6,
        error: null,
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(
      <SourceList items={items} answerKeys={[]} isReprocessing={false} onReprocess={vi.fn()} />,
    );

    expect(screen.getByText("tde12-ders-kitabi.pdf")).toBeInTheDocument();
    expect(screen.getByText("Ders kitabı")).toBeInTheDocument();
    expect(screen.getByText(/2\/6/)).toBeInTheDocument();

    const segments = screen.getAllByTestId("step-segment");
    expect(segments).toHaveLength(6);
    const completed = segments.filter((segment) => !segment.className.includes("bg-navy-soft"));
    expect(completed).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Yeniden işle" })).not.toBeInTheDocument();
  });

  test("hatalı dosyada hata metnini ekranda gösterir (Kabul Kriteri 2)", () => {
    const items: SourceListItem[] = [
      {
        sourceId: 102,
        fileName: "bozuk-dosya.pdf",
        kind: "TEST",
        status: "FAILED",
        lastCompletedStep: "VALIDATE",
        stepIndex: 3,
        totalSteps: 6,
        error: "PDF sayfası okunamadı, dosya bozuk olabilir.",
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(
      <SourceList items={items} answerKeys={[]} isReprocessing={false} onReprocess={vi.fn()} />,
    );

    expect(screen.getByText("bozuk-dosya.pdf")).toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("PDF sayfası okunamadı, dosya bozuk olabilir.");
    expect(screen.getByText("Başarısız")).toBeInTheDocument();
  });

  test("inceleme bekleyen dosyada inceleme rozetini gösterir", () => {
    const items: SourceListItem[] = [
      {
        sourceId: 103,
        fileName: "soru-bankasi.pdf",
        kind: "QUESTION_BANK",
        status: "REVIEW",
        lastCompletedStep: "OUTCOMES",
        stepIndex: 5,
        totalSteps: 6,
        error: null,
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(
      <SourceList items={items} answerKeys={[]} isReprocessing={false} onReprocess={vi.fn()} />,
    );

    expect(screen.getByText("soru-bankasi.pdf")).toBeInTheDocument();
    expect(screen.getByText("İnceleme listesinde")).toBeInTheDocument();
  });

  test("biten testte anahtar seçilince bağlayıp, düğmeyle de anahtarsız yeniden işler", () => {
    const onReprocess = vi.fn();
    const base = {
      lastCompletedStep: "INDEX" as const,
      stepIndex: 6,
      totalSteps: 6,
      error: null,
      createdAt: "2026-11-02T10:00:00Z",
    };
    const test14: SourceListItem = {
      ...base,
      sourceId: 104,
      fileName: "14.pdf",
      kind: "TEST",
      status: "REVIEW",
    };
    const answerKey: SourceListItem = {
      ...base,
      sourceId: 7,
      fileName: "CEVAP_ANAHTARI.pdf",
      kind: "ANSWER_KEY",
      status: "PUBLISHED",
    };

    render(
      <SourceList
        items={[test14]}
        answerKeys={[answerKey]}
        isReprocessing={false}
        onReprocess={onReprocess}
      />,
    );
    fireEvent.change(screen.getByLabelText("Anahtar bağla ve yeniden işle"), {
      target: { value: "7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Yeniden işle" }));

    expect(onReprocess).toHaveBeenNthCalledWith(1, 104, 7);
    expect(onReprocess).toHaveBeenNthCalledWith(2, 104);
  });
});
