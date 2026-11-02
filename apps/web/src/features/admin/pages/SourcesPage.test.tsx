/**
 * SourcesPage bileşeninin rol yetkilendirme, dosya doğrulama ve yükleme davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import SourcesPage from "./SourcesPage";

const { useMeMock, useUploadSourcesMock, mutateMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
  useUploadSourcesMock: vi.fn(),
  mutateMock: vi.fn(),
}));

vi.mock("../../auth/api", () => ({
  useMe: useMeMock,
}));

vi.mock("../api", () => ({
  useUploadSources: useUploadSourcesMock,
}));

const adminUser = {
  id: 1,
  email: "admin@example.com",
  displayName: "Admin",
  role: "CONTENT_ADMIN",
  grade: null,
  explainStyle: "DETAILED",
};

const studentUser = {
  ...adminUser,
  id: 2,
  role: "STUDENT",
};

/** Sayfayı bellek içi yönlendiriciyle sarmalayarak render eder. */
function renderSourcesPage() {
  return render(
    <MemoryRouter initialEntries={["/admin/sources"]}>
      <SourcesPage />
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("SourcesPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    useMeMock.mockReturnValue({ data: adminUser, isPending: false });
    useUploadSourcesMock.mockReturnValue({
      mutate: mutateMock,
      isPending: false,
      isError: false,
      data: null,
      error: null,
    });
  });

  test("oturum açmamış kullanıcıyı render etmez veya login'e yönlendirir", () => {
    useMeMock.mockReturnValue({ data: null, isPending: false });
    renderSourcesPage();

    expect(screen.queryByText("PDF'leri buraya bırak")).not.toBeInTheDocument();
  });

  test("CONTENT_ADMIN olmayan kullanıcıya erişim engeli gösterir", () => {
    useMeMock.mockReturnValue({ data: studentUser, isPending: false });
    renderSourcesPage();

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Bu ekranı yalnızca içerik yöneticileri görüntüleyebilir.",
    );
    expect(screen.queryByText("PDF'leri buraya bırak")).not.toBeInTheDocument();
  });

  test("PDF olmayan dosya seçildiğinde sunucuya istek atmadan uyarır", async () => {
    renderSourcesPage();

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const txtFile = new File(["not a pdf"], "deneme.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [txtFile] } });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Yalnızca PDF dosyaları yüklenebilir.");
    });
    expect(mutateMock).not.toHaveBeenCalled();
  });

  test("geçerli birden çok PDF seçildiğinde tek mutation çağrısı yapar", async () => {
    renderSourcesPage();

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdf1 = new File(["pdf1"], "kitap1.pdf", { type: "application/pdf" });
    const pdf2 = new File(["pdf2"], "kitap2.pdf", { type: "application/pdf" });

    fireEvent.change(input, { target: { files: [pdf1, pdf2] } });

    await waitFor(() => {
      expect(mutateMock).toHaveBeenCalledTimes(1);
    });
    expect(mutateMock).toHaveBeenCalledWith([pdf1, pdf2]);
  });

  test("sunucudan duplicate yanıtı geldiğinde ilgili dosya için uyarı gösterir", () => {
    useUploadSourcesMock.mockReturnValue({
      mutate: mutateMock,
      isPending: false,
      isError: false,
      data: {
        files: [
          { sourceId: 101, fileName: "yeni.pdf", duplicate: false },
          { sourceId: 102, fileName: "eski.pdf", duplicate: true },
        ],
      },
      error: null,
    });

    renderSourcesPage();

    expect(screen.getByText("yeni.pdf")).toBeInTheDocument();
    expect(screen.getByText("eski.pdf")).toBeInTheDocument();
    expect(screen.getByText("Bu dosya daha önce yüklenmiş")).toBeInTheDocument();
  });

  test("sunucu hatası oluştuğunda hata mesajını ekranda gösterir", () => {
    const error = new ApiError({ code: "FILE_TOO_LARGE" }, 413);
    useUploadSourcesMock.mockReturnValue({
      mutate: mutateMock,
      isPending: false,
      isError: true,
      data: null,
      error,
    });

    renderSourcesPage();

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  test("yükleme sürerken butonu devre dışı bırakır ve durum metnini gösterir", () => {
    useUploadSourcesMock.mockReturnValue({
      mutate: mutateMock,
      isPending: true,
      isError: false,
      data: null,
      error: null,
    });

    renderSourcesPage();

    const button = screen.getByRole("button", { name: "Yükleniyor..." });
    expect(button).toBeDisabled();
  });
});
