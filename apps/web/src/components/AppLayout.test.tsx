/**
 * AppLayout bileşeninin temel davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { test, expect, vi } from "vitest";
import { MemoryRouter } from "react-router";
import "../lib/i18n";
import AppLayout from "./AppLayout";

vi.mock("../features/auth/api", () => ({
  /** Testlerde oturum açılmamış kullanıcıyı temsil eder. */
  useMe: () => ({ data: null }),

  /** Testlerde çıkış işlemini taklit eder. */
  useLogout: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

/** Uygulama adının bağlantı olarak görüntülendiğini doğrular. */
function rendersAppName() {
  render(
    <MemoryRouter>
      <AppLayout />
    </MemoryRouter>,
  );

  expect(screen.getByRole("link", { name: "Bilig" })).toBeInTheDocument();
}

test("uygulama adını gösterir", rendersAppName);
