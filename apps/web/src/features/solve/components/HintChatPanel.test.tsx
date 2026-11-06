/**
 * HintChatPanel bileşeninin karşılama, ipucu isteme ve serbest yazı davranışını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import HintChatPanel from "./HintChatPanel";

afterEach(cleanup);

/** Paneli verilen özelliklerle ve varsayılan boş durumla çizer. */
function renderPanel(overrides: Partial<Parameters<typeof HintChatPanel>[0]> = {}) {
  return render(
    <HintChatPanel
      messages={[]}
      error={null}
      isHintPending={false}
      isStreaming={false}
      isLimitReached={false}
      onRequestHint={vi.fn()}
      onSendMessage={vi.fn()}
      {...overrides}
    />,
  );
}

describe("HintChatPanel", () => {
  test("karşılama mesajını gösterir", () => {
    renderPanel();

    expect(screen.getByRole("heading", { name: "Soru asistanı" })).toBeInTheDocument();
    expect(screen.getByText(/Soruda takıldığın yerde bana yazabilirsin/)).toBeInTheDocument();
  });

  test("ipucu al düğmesine basınca ipucu ister", () => {
    const onRequestHint = vi.fn();
    renderPanel({ onRequestHint });

    fireEvent.click(screen.getByRole("button", { name: "İpucu al" }));

    expect(onRequestHint).toHaveBeenCalledTimes(1);
  });

  test("yazılan mesajı gönderir; başka örnek düğmesini göstermez", () => {
    const onSendMessage = vi.fn();
    renderPanel({ onSendMessage });

    fireEvent.change(screen.getByPlaceholderText("Anlamadığın yeri yaz…"), {
      target: { value: "Bu soruda ne isteniyor?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Gönder" }));

    expect(onSendMessage).toHaveBeenCalledWith("Bu soruda ne isteniyor?");
    expect(screen.queryByRole("button", { name: "Başka örnekle anlat" })).not.toBeInTheDocument();
  });

  test("gelen mesajı ve hatayı gösterir", () => {
    renderPanel({
      messages: [{ id: "h1", role: "assistant", text: "Genel mesaja bak.", citationBlockIds: [] }],
      error: "İpucu alınamadı.",
    });

    expect(screen.getByText("Genel mesaja bak.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("İpucu alınamadı.");
  });
});
