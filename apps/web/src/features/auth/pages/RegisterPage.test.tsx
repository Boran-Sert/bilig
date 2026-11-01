/* eslint-disable i18next/no-literal-string */
/**
 * RegisterPage bileşeninin kayıt davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import RegisterPage from "./RegisterPage";

const { mutateAsync, useRegisterMock } = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  useRegisterMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useRegister: useRegisterMock,
}));

/** Giriş rotası. */
function LoginLocation() {
  const location = useLocation();

  return (
    <div>
      <span>Giriş sayfası</span>
      <span>{location.state?.message}</span>
    </div>
  );
}

/** Kayıt sayfasını oluşturur. */
function renderRegisterPage() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginLocation />} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Kayıt formunu doldurur. */
function fillRegisterForm() {
  fireEvent.change(screen.getByLabelText(/ad soyad/i), {
    target: { value: "Test Kullanıcı" },
  });

  fireEvent.change(screen.getByLabelText(/e-posta/i), {
    target: { value: "test@example.com" },
  });

  fireEvent.change(screen.getByLabelText(/şifre/i), {
    target: { value: "Test1234" },
  });
}

afterEach(cleanup);

describe("RegisterPage", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    useRegisterMock.mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
      error: null,
    });
  });

  test("zorunlu alanlar boşken doğrulama hatalarını gösterir", async () => {
    renderRegisterPage();

    fireEvent.click(screen.getByRole("button", { name: /kayıt ol/i }));

    expect(await screen.findAllByText("Bu alan zorunludur.")).not.toHaveLength(0);
    expect(screen.getByText(/en az 8 karakter/i)).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  test("geçerli bilgilerle kayıt isteği gönderir", async () => {
    mutateAsync.mockResolvedValue({
      id: "1",
      email: "test@example.com",
      displayName: "Test Kullanıcı",
    });

    renderRegisterPage();
    fillRegisterForm();

    fireEvent.click(screen.getByRole("button", { name: /kayıt ol/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          displayName: "Test Kullanıcı",
          email: "test@example.com",
          password: "Test1234",
        }),
      );
    });
  });

  test("başarılı kayıt sonrası giriş sayfasına yönlendirir", async () => {
    mutateAsync.mockResolvedValue({
      id: "1",
      email: "test@example.com",
      displayName: "Test Kullanıcı",
    });

    renderRegisterPage();
    fillRegisterForm();

    fireEvent.click(screen.getByRole("button", { name: /kayıt ol/i }));

    expect(await screen.findByText("Giriş sayfası")).toBeInTheDocument();

    expect(await screen.findByText("Hesabın oluşturuldu. Giriş yapabilirsin.")).toBeInTheDocument();
  });

  test("kayıt hatasını gösterir", async () => {
    useRegisterMock.mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: true,
      error: { code: "EMAIL_TAKEN" },
    });

    renderRegisterPage();

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
