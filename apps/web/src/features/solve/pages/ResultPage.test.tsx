/**
 * ResultPage bileşeninin net hesaplama, kazanım sıralama ve vurgulamalarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import "../../../lib/i18n";
import type { SessionCompletionResponse } from "../types";
import ResultPage from "./ResultPage";

const mockResult: SessionCompletionResponse = {
  correct: 18,
  wrong: 4,
  blank: 2,
  net: 17.0,
  outcomes: [
    {
      code: "A.2.3",
      title: "Tema ve konu",
      wrong: 1,
      failed: false,
    },
    {
      code: "A.2.15",
      title: "Türün yazar ve eserleri",
      wrong: 3,
      failed: true,
    },
    {
      code: "A.1.1",
      title: "Metinde geçen kelimeler",
      wrong: 0,
      failed: false,
    },
  ],
};

/** Sonuç sayfasını verilen state ile oluşturur. */
function renderResultPage(result?: SessionCompletionResponse) {
  return render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: "/tests/1/result",
          state: result ? { result } : undefined,
        },
      ]}
    >
      <Routes>
        <Route path="/tests/:testId/result" element={<ResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("ResultPage", () => {
  test("net ve soru sayılarını sunucudaki değerlerle aynı gösterir (Kabul Kriteri 1)", () => {
    renderResultPage(mockResult);

    expect(screen.getByText("17,00")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
    expect(screen.getByText("Doğru")).toBeInTheDocument();
    expect(screen.getByText("Yanlış")).toBeInTheDocument();
    expect(screen.getByText("Boş")).toBeInTheDocument();
  });

  test("başarısız kazanımı en üstte sıralar ve vurgular (Kabul Kriteri 2)", () => {
    renderResultPage(mockResult);

    const outcomeElements = screen.getAllByRole("listitem");
    expect(outcomeElements).toHaveLength(3);

    expect(outcomeElements[0]).toHaveTextContent("A.2.15");
    expect(outcomeElements[0]).toHaveTextContent("Türün yazar ve eserleri");
    expect(outcomeElements[0]).toHaveTextContent("Başarısız");
    expect(outcomeElements[0]).toHaveTextContent("3 yanlış");

    expect(outcomeElements[1]).toHaveTextContent("A.2.3");
    expect(outcomeElements[1]).toHaveTextContent("Başarılı");
    expect(outcomeElements[2]).toHaveTextContent("A.1.1");
    expect(outcomeElements[2]).toHaveTextContent("Başarılı");
  });

  test("sonuç bilgisi olmadığında boş durum uyarısı gösterir", () => {
    renderResultPage(undefined);

    expect(screen.getByText("Görüntülenecek test sonucu bulunamadı.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Testlere Dön" })).toBeInTheDocument();
  });
});
