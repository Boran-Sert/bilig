/**
 * RequireAuth bileşeninin oturum kontrolünü test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import RequireAuth from "./RequireAuth";

const { useMeMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useMe: useMeMock,
}));

/** Giriş sayfasını ve yönlendirmede taşınan adresi gösterir. */
function LoginLocation() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from;

  return <h1>Giriş sayfası {from?.pathname}</h1>;
}

/** Korumalı sayfayı test yönlendiricisiyle oluşturur. */
function renderProtectedPage() {
  return render(
    <MemoryRouter initialEntries={["/private"]}>
      <Routes>
        <Route
          path="/private"
          element={
            <RequireAuth>
              <h1>Korumalı içerik</h1>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<LoginLocation />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("RequireAuth", () => {
  beforeEach(() => {
    useMeMock.mockReset();
  });

  test("oturum yüklenirken içeriği göstermez", () => {
    useMeMock.mockReturnValue({ data: undefined, isPending: true, isError: false });

    renderProtectedPage();

    expect(screen.queryByText("Korumalı içerik")).not.toBeInTheDocument();
    expect(screen.queryByText(/Giriş sayfası/)).not.toBeInTheDocument();
  });

  test("oturum varsa korumalı içeriği gösterir", () => {
    useMeMock.mockReturnValue({ data: { id: 1 }, isPending: false, isError: false });

    renderProtectedPage();

    expect(screen.getByText("Korumalı içerik")).toBeInTheDocument();
  });

  test("oturum yoksa geldiği adresle giriş sayfasına yönlendirir", () => {
    useMeMock.mockReturnValue({ data: null, isPending: false, isError: false });

    renderProtectedPage();

    expect(screen.getByText("Giriş sayfası /private")).toBeInTheDocument();
  });

  test("sunucu hatasında yönlendirmeden hata gösterir", () => {
    useMeMock.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new ApiError({ code: "INTERNAL_ERROR", detail: "Beklenmeyen hata." }, 500),
    });

    renderProtectedPage();

    expect(screen.getByRole("alert")).toHaveTextContent("Beklenmeyen hata.");
    expect(screen.queryByText(/Giriş sayfası/)).not.toBeInTheDocument();
  });
});
