/**
 * LoginPage bileşeninin giriş davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import LoginPage from "./LoginPage";

const { useLoginMock, mutateMock } = vi.hoisted(() => ({
  useLoginMock: vi.fn(),
  mutateMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useLogin: useLoginMock,
}));

/** Giriş sayfasını isteğe bağlı yönlendirme durumuyla oluşturur. */
function renderLoginPage(state?: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state }]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Ana sayfa</h1>} />
        <Route path="/private" element={<h1>Korumalı sayfa</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Formu doldurup gönderir. */
function submitLoginForm() {
  fireEvent.change(screen.getByLabelText("E-posta adresi"), {
    target: { value: "test@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: "password123" } });
  fireEvent.click(screen.getByRole("button", { name: "Giriş yap" }));
}

/** Giriş hook'unu verilen hata durumuyla taklit eder. */
function mockLoginState(error: ApiError | null) {
  useLoginMock.mockReturnValue({
    mutate: mutateMock,
    isPending: false,
    isError: error !== null,
    error,
  });
}

afterEach(cleanup);

describe("LoginPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    mockLoginState(null);
  });

  test("sayfa başlığını ve beni hatırla varsayılanını ayarlar", () => {
    renderLoginPage();

    expect(document.title).toBe("Giriş yap · Bilig");
    expect(screen.getByRole("checkbox", { name: "Beni hatırla" })).not.toBeChecked();
  });

  test("boş formu da arayüzde engellemeden sunucuya gönderir", async () => {
    renderLoginPage();

    fireEvent.click(screen.getByRole("button", { name: "Giriş yap" }));

    await waitFor(() => {
      expect(mutateMock).toHaveBeenCalledWith(
        { email: "", password: "", rememberMe: false },
        expect.anything(),
      );
    });
  });

  test("başarılı girişte geldiği sayfaya yönlendirir", async () => {
    mutateMock.mockImplementation((_values, options) => options.onSuccess());
    renderLoginPage({ from: { pathname: "/private" } });

    submitLoginForm();

    expect(await screen.findByText("Korumalı sayfa")).toBeInTheDocument();
  });

  test("sunucunun alan hatasını ilgili alanın altında gösterir", async () => {
    const error = new ApiError(
      {
        code: "VALIDATION_FAILED",
        errors: [{ field: "email", message: "Geçerli bir e-posta adresi gir." }],
      },
      400,
    );
    mutateMock.mockImplementation((_values, options) => options.onError(error));
    renderLoginPage();

    submitLoginForm();

    expect(await screen.findByText("Geçerli bir e-posta adresi gir.")).toBeInTheDocument();
    expect(screen.getByLabelText("E-posta adresi")).toHaveAttribute("aria-invalid", "true");
  });

  test("hatalı şifrede sunucunun hata kodunu mesaja çevirir", () => {
    mockLoginState(new ApiError({ code: "INVALID_CREDENTIALS" }, 401));

    renderLoginPage();

    expect(screen.getByRole("alert")).toHaveTextContent("E-posta adresi veya şifre hatalı.");
  });
});
