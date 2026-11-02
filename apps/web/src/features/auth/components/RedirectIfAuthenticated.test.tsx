/**
 * RedirectIfAuthenticated bileşeninin misafir sayfası kontrolünü test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import RedirectIfAuthenticated from "./RedirectIfAuthenticated";

const { useMeMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useMe: useMeMock,
}));

/** Giriş sayfasını belirtilen yönlendirme durumuyla oluşturur. */
function renderLoginPage(state?: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state }]}>
      <Routes>
        <Route
          path="/login"
          element={
            <RedirectIfAuthenticated>
              <h1>Giriş formu</h1>
            </RedirectIfAuthenticated>
          }
        />
        <Route path="/" element={<h1>Ana sayfa</h1>} />
        <Route path="/private" element={<h1>Korumalı sayfa</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("RedirectIfAuthenticated", () => {
  beforeEach(() => {
    useMeMock.mockReset();
  });

  test("oturum yoksa misafir içeriğini gösterir", () => {
    useMeMock.mockReturnValue({ data: null, isPending: false });

    renderLoginPage();

    expect(screen.getByText("Giriş formu")).toBeInTheDocument();
  });

  test("oturum varsa ana sayfaya yönlendirir", () => {
    useMeMock.mockReturnValue({ data: { id: 1 }, isPending: false });

    renderLoginPage();

    expect(screen.getByText("Ana sayfa")).toBeInTheDocument();
  });

  test("oturum varsa geldiği sayfaya yönlendirir", () => {
    useMeMock.mockReturnValue({ data: { id: 1 }, isPending: false });

    renderLoginPage({ from: { pathname: "/private" } });

    expect(screen.getByText("Korumalı sayfa")).toBeInTheDocument();
  });
});
