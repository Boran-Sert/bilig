/**
 * Ortak sayfa düzeninin başlık ve çıkış davranışını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import "../lib/i18n";
import { ApiError } from "../lib/api/problem";
import AppLayout from "./AppLayout";

const { useMeMock, useLogoutMock, mutateMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
  useLogoutMock: vi.fn(),
  mutateMock: vi.fn(),
}));

vi.mock("../features/auth/api", () => ({
  useMe: useMeMock,
  useLogout: useLogoutMock,
}));

/** Düzeni giriş rotasıyla birlikte oluşturur. */
function renderLayout() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<h1>Ana sayfa</h1>} />
          <Route path="/login" element={<h1>Giriş sayfası</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

/** Çıkış hook'unu verilen hata durumuyla taklit eder. */
function mockLogoutState(error: ApiError | null) {
  useLogoutMock.mockReturnValue({
    mutate: mutateMock,
    isPending: false,
    isError: error !== null,
    error,
  });
}

afterEach(cleanup);

describe("AppLayout", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    useMeMock.mockReturnValue({ data: { id: 1 } });
    mockLogoutState(null);
  });

  test("uygulama adını bağlantı olarak gösterir", () => {
    useMeMock.mockReturnValue({ data: null });

    renderLayout();

    expect(screen.getByRole("link", { name: "Bilig" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Çıkış yap" })).not.toBeInTheDocument();
  });

  test("çıkış başarılıysa giriş sayfasına gider", async () => {
    mutateMock.mockImplementation((_variables, options) => options.onSuccess());

    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Çıkış yap" }));

    expect(await screen.findByText("Giriş sayfası")).toBeInTheDocument();
  });

  test("çıkış başarısızsa hatayı gösterir", () => {
    mockLogoutState(new ApiError({ code: "INTERNAL_ERROR", detail: "Çıkış yapılamadı." }, 500));

    renderLayout();

    expect(screen.getByRole("alert")).toHaveTextContent("Çıkış yapılamadı.");
    expect(screen.getByText("Ana sayfa")).toBeInTheDocument();
  });
});
