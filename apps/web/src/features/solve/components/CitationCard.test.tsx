/**
 * CitationCard ve PageImageDialog bileşenlerinin alıntı ve sayfa görüntüsü davranışını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import CitationCard from "./CitationCard";

const { useBlockMock } = vi.hoisted(() => ({
  useBlockMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useBlock: useBlockMock,
}));

afterEach(cleanup);

describe("CitationCard", () => {
  beforeEach(() => {
    useBlockMock.mockReset();
  });

  test("kaynak başlığını, sayfa numarasını ve alıntı metnini gösterir", () => {
    useBlockMock.mockReturnValue({
      data: {
        id: 10,
        markdown: "Tarihî romanlar konusunu tarihten alır.",
        sourceTitle: "TDE 12 Ders Kitabı",
        pageNo: 174,
        pageId: 44,
      },
      isPending: false,
    });

    render(<CitationCard blockId={10} />);

    expect(screen.getByText(/DERS KİTABINDA/)).toBeInTheDocument();
    expect(screen.getByText(/TDE 12 Ders Kitabı/)).toBeInTheDocument();
    expect(screen.getByText(/s\. 174/)).toBeInTheDocument();
    expect(screen.getByText(/“Tarihî romanlar konusunu tarihten alır\.”/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sayfayı aç" })).toBeInTheDocument();
  });

  test("Sayfayı aç tıklandığında sayfa görseli penceresini açar ve kapatır", () => {
    useBlockMock.mockReturnValue({
      data: {
        id: 10,
        markdown: "Örnek alıntı metni",
        sourceTitle: "TDE 12 Ders Kitabı",
        pageNo: 174,
        pageId: 44,
      },
      isPending: false,
    });

    render(<CitationCard blockId={10} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sayfayı aç" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("src", "/api/pages/44/image");

    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
