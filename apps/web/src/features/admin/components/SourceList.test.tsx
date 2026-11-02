/**
 * SourceList bileşeninin 8 adım gösterimini, durum rozetlerini ve hata metnini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import "../../../lib/i18n";
import type { SourceListItem } from "../types";
import SourceList from "./SourceList";

afterEach(cleanup);

describe("SourceList", () => {
  test("boş liste verildiğinde boş liste uyarısını gösterir", () => {
    render(<SourceList items={[]} />);
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
        stepIndex: 3,
        totalSteps: 8,
        error: null,
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(<SourceList items={items} />);

    expect(screen.getByText("tde12-ders-kitabi.pdf")).toBeInTheDocument();
    expect(screen.getByText("Ders kitabı")).toBeInTheDocument();
    expect(screen.getByText(/3\/8/)).toBeInTheDocument();

    const segments = screen.getAllByTestId("step-segment");
    expect(segments).toHaveLength(8);
  });

  test("hatalı dosyada hata metnini ekranda gösterir (Kabul Kriteri 2)", () => {
    const items: SourceListItem[] = [
      {
        sourceId: 102,
        fileName: "bozuk-dosya.pdf",
        kind: "TEST",
        status: "FAILED",
        lastCompletedStep: "VALIDATE",
        stepIndex: 2,
        totalSteps: 8,
        error: "PDF sayfası okunamadı, dosya bozuk olabilir.",
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(<SourceList items={items} />);

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
        stepIndex: 6,
        totalSteps: 8,
        error: null,
        createdAt: "2026-11-02T10:00:00Z",
      },
    ];

    render(<SourceList items={items} />);

    expect(screen.getByText("soru-bankasi.pdf")).toBeInTheDocument();
    expect(screen.getByText("İnceleme listesinde")).toBeInTheDocument();
  });
});
