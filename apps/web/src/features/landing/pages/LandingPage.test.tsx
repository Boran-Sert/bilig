/**
 * LandingPage bileşeninin ziyaretçiye tanıtımı, girişli kullanıcıyı panele yönlendirmesini test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import LandingPage from "./LandingPage";

const { useMeMock } = vi.hoisted(() => ({ useMeMock: vi.fn() }));

vi.mock("../../auth/api", () => ({ useMe: useMeMock }));

/** Karşılama sayfasını panel rotasıyla birlikte oluşturur. */
function renderLanding() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/panel" element={<h1>Panel sayfası</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("LandingPage", () => {
  test("ziyaretçiye başlığı, kurumlar bölümünü ve kayıt bağlantısını gösterir", () => {
    useMeMock.mockReturnValue({ data: null, isPending: false });

    renderLanding();

    expect(
      screen.getByRole("heading", { name: "Eğitimde yeni nesil, yapay zeka destekli öğretim" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Kurumunuza özel entegrasyon" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Ücretsiz başla" })[0]).toHaveAttribute(
      "href",
      "/register",
    );
    expect(screen.getByText("iletisim@ornek.com")).toBeInTheDocument();
  });

  test("oturum açıksa panele yönlendirir", () => {
    useMeMock.mockReturnValue({ data: { id: 1 }, isPending: false });

    renderLanding();

    expect(screen.getByText("Panel sayfası")).toBeInTheDocument();
  });
});
