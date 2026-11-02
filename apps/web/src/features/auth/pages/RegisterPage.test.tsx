/**
 * RegisterPage bileşeninin kayıt davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import RegisterPage from "./RegisterPage";

const { mutateMock, useRegisterMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
  useRegisterMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useRegister: useRegisterMock,
}));

/** Kayıt sayfasını test yönlendiricisiyle oluşturur. */
function renderRegisterPage() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<h1>Ana sayfa</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Kayıt formunu verilen parolayla doldurur. */
function fillRegisterForm(password = "Test1234") {
  fireEvent.change(screen.getByLabelText("Görünen ad"), { target: { value: "Kitapkurdu" } });
  fireEvent.change(screen.getByLabelText("E-posta adresi"), {
    target: { value: "test@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: password } });
}

/** Formu gönderir. */
function submitRegisterForm() {
  fireEvent.click(screen.getByRole("button", { name: "Kayıt ol" }));
}

/** Kayıt hook'unu verilen hata durumuyla taklit eder. */
function mockRegisterState(error: ApiError | null) {
  useRegisterMock.mockReturnValue({
    mutate: mutateMock,
    isPending: false,
    isError: error !== null,
    error,
  });
}

afterEach(cleanup);

describe("RegisterPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    mockRegisterState(null);
  });

  test("sayfa başlığını ayarlar ve anlatım tarzı ile sınıf sormaz", () => {
    renderRegisterPage();

    expect(document.title).toBe("Hesap oluştur · Bilig");
    expect(screen.queryByText("Sade")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Sınıf")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/aydınlatma metnini okudum/)).not.toBeChecked();
    expect(screen.getByLabelText(/açık rıza veriyorum/)).not.toBeChecked();
  });

  test("kısa parolayı istek atmadan uyarır", async () => {
    renderRegisterPage();
    fillRegisterForm("kisa");

    submitRegisterForm();

    expect(await screen.findByText("Şifre en az 8 karakter olmalıdır.")).toBeInTheDocument();
    expect(mutateMock).not.toHaveBeenCalled();
  });

  test("72 baytı aşan parolayı istek atmadan uyarır", async () => {
    renderRegisterPage();
    fillRegisterForm("ğ".repeat(37));

    submitRegisterForm();

    expect(await screen.findByText("Şifre en fazla 72 bayt olabilir.")).toBeInTheDocument();
    expect(mutateMock).not.toHaveBeenCalled();
  });

  test("diğer alanları arayüzde denetlemeden iki onayı ayrı gönderir", async () => {
    renderRegisterPage();
    fillRegisterForm();
    fireEvent.click(screen.getByLabelText(/açık rıza veriyorum/));

    submitRegisterForm();

    await waitFor(() => {
      expect(mutateMock).toHaveBeenCalledWith(
        {
          displayName: "Kitapkurdu",
          email: "test@example.com",
          password: "Test1234",
          privacyNoticeAccepted: false,
          consentAccepted: true,
        },
        expect.anything(),
      );
    });
  });

  test("başarılı kayıtta oturum açık olarak ana sayfaya gider", async () => {
    mutateMock.mockImplementation((_values, options) => options.onSuccess());
    renderRegisterPage();
    fillRegisterForm();

    submitRegisterForm();

    expect(await screen.findByText("Ana sayfa")).toBeInTheDocument();
  });

  test("sunucunun onay ve e-posta hatalarını kendi alanlarının altında gösterir", async () => {
    const error = new ApiError(
      {
        code: "VALIDATION_FAILED",
        errors: [
          { field: "privacyNoticeAccepted", message: "Aydınlatma metnini onaylamalısın." },
          { field: "consentAccepted", message: "Açık rıza vermelisin." },
          { field: "email", message: "Geçerli bir e-posta adresi gir." },
        ],
      },
      400,
    );
    mutateMock.mockImplementation((_values, options) => options.onError(error));
    renderRegisterPage();
    fillRegisterForm();

    submitRegisterForm();

    expect(await screen.findByText("Aydınlatma metnini onaylamalısın.")).toBeInTheDocument();
    expect(screen.getByLabelText(/aydınlatma metnini okudum/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByText("Açık rıza vermelisin.")).toBeInTheDocument();
    expect(screen.getByLabelText(/açık rıza veriyorum/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Geçerli bir e-posta adresi gir.")).toBeInTheDocument();
  });

  test("kayıtlı e-postada sunucunun hata kodunu mesaja çevirir", () => {
    mockRegisterState(new ApiError({ code: "EMAIL_TAKEN" }, 409));

    renderRegisterPage();

    expect(screen.getByRole("alert")).toHaveTextContent("Bu e-posta adresi zaten kayıtlı.");
  });
});
