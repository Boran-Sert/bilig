/* eslint-disable i18next/no-literal-string */
/**
 * RequireAuth bileşeninin oturum kontrolünü test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import RequireAuth from "./RequireAuth";

const { useMeMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
}));

vi.mock("../api", () => ({
  useMe: useMeMock,
}));

/**
 * Test sayfalarını oluşturur.
 * @returns Test sayfalarının görünümü.
 */
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
        <Route path="/login" element={<h1>Giriş sayfası</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  beforeEach(() => {
    useMeMock.mockReset();
  });

  test("oturum yüklenirken içeriği göstermez", () => {
    useMeMock.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    });

    renderProtectedPage();

    expect(screen.queryByText("Korumalı içerik")).not.toBeInTheDocument();
    expect(screen.queryByText("Giriş sayfası")).not.toBeInTheDocument();
  });

  test("oturum varsa korumalı içeriği gösterir", () => {
    useMeMock.mockReturnValue({
      data: { id: "1", email: "test@example.com" },
      isPending: false,
      isError: false,
    });

    renderProtectedPage();

    expect(screen.getByText("Korumalı içerik")).toBeInTheDocument();
  });

  test("oturum yoksa giriş sayfasına yönlendirir", () => {
    useMeMock.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    });

    renderProtectedPage();

    expect(screen.getByText("Giriş sayfası")).toBeInTheDocument();
  });
});
