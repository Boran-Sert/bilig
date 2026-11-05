/**
 * ChatInputBar bileşeninin mesaj gönderimi, hızlı eylem ve limit kilidini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import ChatInputBar from "./ChatInputBar";

afterEach(cleanup);

describe("ChatInputBar", () => {
  test("mesaj yazılıp Gönder butonuna basıldığında iletir", () => {
    const handleSend = vi.fn();
    render(<ChatInputBar onSendMessage={handleSend} isStreaming={false} isLimitReached={false} />);

    const input = screen.getByPlaceholderText("Anlamadığın yeri yaz…");
    const sendButton = screen.getByRole("button", { name: "Gönder" });

    fireEvent.change(input, { target: { value: "Küçük Ağa kimin eseri?" } });
    fireEvent.click(sendButton);

    expect(handleSend).toHaveBeenCalledWith("Küçük Ağa kimin eseri?");
    expect(input).toHaveValue("");
  });

  test("Başka örnekle anlat butonuna tıklandığında hazır istemi gönderir", () => {
    const handleSend = vi.fn();
    render(<ChatInputBar onSendMessage={handleSend} isStreaming={false} isLimitReached={false} />);

    const exampleButton = screen.getByRole("button", { name: "Başka örnekle anlat" });
    fireEvent.click(exampleButton);

    expect(handleSend).toHaveBeenCalledWith("Başka bir örnekle açıklar mısın?");
  });

  test("limit dolduğunda girdiyi ve hızlı eylemi kilitler", () => {
    const handleSend = vi.fn();
    render(<ChatInputBar onSendMessage={handleSend} isStreaming={false} isLimitReached={true} />);

    const input = screen.getByPlaceholderText("Günlük mesaj limitine ulaşıldı.");
    expect(input).toBeDisabled();
    expect(screen.getByRole("button", { name: "Başka örnekle anlat" })).toBeDisabled();
  });
});
