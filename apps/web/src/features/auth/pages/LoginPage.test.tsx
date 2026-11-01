/* eslint-disable i18next/no-literal-string */
/**
 * LoginPage bileşeninin giriş davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import "../../../lib/i18n";
import LoginPage from "./LoginPage";

const { useLoginMock, mutateAsyncMock } = vi.hoisted(() => ({
  useLoginMock: vi.fn(),
  mutateAsyncMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useLogin: useLoginMock,
}));

/**
 * Giriş sayfasını test ortamında oluşturur.
 */
function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Ana sayfa</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset();
    useLoginMock.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
      isError: false,
      error: null,
    });
  });

  test("remember me varsayılan olarak seçili değildir", () => {
    renderLoginPage();

    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });

  test("başarılı girişte ana sayfaya yönlendirir", async () => {
    mutateAsyncMock.mockResolvedValue({ id: "1" });
    renderLoginPage();

    fireEvent.change(screen.getByLabelText("E-posta adresi"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Şifre"), {
      target: { value: "password123" },
    });
    fireEvent.submit(screen.getByLabelText("E-posta adresi").closest("form")!);

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
        rememberMe: false,
      });
    });

    expect(await screen.findByText("Ana sayfa")).toBeInTheDocument();
  });

  test("hatalı giriş mesajını gösterir", () => {
    useLoginMock.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
      isError: true,
      error: { code: "INVALID_CREDENTIALS" },
    });

    renderLoginPage();

    expect(screen.getByRole("alert")).toHaveTextContent("E-posta adresi veya şifre hatalı.");
  });
});
