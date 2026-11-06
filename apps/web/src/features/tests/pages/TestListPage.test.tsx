/**
 * TestListPage bileşeninin test listeleme ve başlama/devam etme davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import TestListPage from "./TestListPage";

const { useTestsMock, navigateMock } = vi.hoisted(() => ({
  useTestsMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    /** Test için navigate mock döner. */
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../solve/api", () => ({
  useTests: useTestsMock,
}));

afterEach(cleanup);

describe("TestListPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useTestsMock.mockReset();
  });

  test("boş test listesi durumunda boş uyarısını gösterir", () => {
    useTestsMock.mockReturnValue({ data: [], isPending: false, isError: false });
    render(
      <MemoryRouter>
        <TestListPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Henüz yayınlanmış bir test bulunmuyor.")).toBeInTheDocument();
  });

  test("testleri ve yarım kalmış testte Devam et butonunu gösterir", () => {
    useTestsMock.mockReturnValue({
      data: [
        {
          id: 1,
          title: "Roman Testi",
          questionCount: 10,
          answeredCount: 0,
          sessionId: null,
          status: null,
        },
        {
          id: 2,
          title: "Şiir Testi",
          questionCount: 10,
          answeredCount: 4,
          sessionId: 99,
          status: null,
        },
      ],
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <TestListPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Roman Testi")).toBeInTheDocument();
    expect(screen.getByText("Şiir Testi")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Başla" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Devam et" })).toBeInTheDocument();
  });

  test("Devam et butonuna tıklandığında çözme sayfasına yönlendirir", () => {
    useTestsMock.mockReturnValue({
      data: [
        {
          id: 2,
          title: "Şiir Testi",
          questionCount: 10,
          answeredCount: 4,
          sessionId: 99,
          status: null,
        },
      ],
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <TestListPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Devam et" }));
    expect(navigateMock).toHaveBeenCalledWith("/tests/2/solve");
  });

  test("arama, ders ve kazanım alanlarını devre dışı gösterir; Tümü kartı gerçek sayıyı verir", () => {
    useTestsMock.mockReturnValue({
      data: [
        {
          id: 1,
          title: "Roman Testi",
          questionCount: 10,
          answeredCount: 0,
          sessionId: null,
          status: null,
        },
      ],
      isPending: false,
      isError: false,
    });

    render(
      <MemoryRouter>
        <TestListPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("searchbox", { name: "Test ara" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Ders" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Kazanım" })).toBeDisabled();
    expect(screen.getByText("1 test")).toBeInTheDocument();
    expect(screen.getAllByText("Yakında")).toHaveLength(4);
  });
});
