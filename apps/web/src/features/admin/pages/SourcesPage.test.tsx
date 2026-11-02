/**
 * SourcesPage bileşeninin yetki, dosya ayıklama ve yükleme davranışlarını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../../lib/i18n";
import { ApiError } from "../../../lib/api/problem";
import SourcesPage from "./SourcesPage";

const { useMeMock, useUploadSourcesMock, useSourcesMock, mutateMock } = vi.hoisted(() => ({
  useMeMock: vi.fn(),
  useUploadSourcesMock: vi.fn(),
  useSourcesMock: vi.fn(),
  mutateMock: vi.fn(),
}));

vi.mock("../../auth/api", () => ({
  useMe: useMeMock,
}));

vi.mock("../api", () => ({
  useUploadSources: useUploadSourcesMock,
  useSources: useSourcesMock,
}));

const contentManager = {
  id: 1,
  email: "admin@example.com",
  displayName: "Admin",
  role: "ADMIN",
  grade: null,
  explainStyle: "SIMPLE",
  canManageContent: true,
};

/** Sayfayı bellek içi yönlendiriciyle oluşturur. */
function renderSourcesPage() {
  return render(
    <MemoryRouter initialEntries={["/admin/sources"]}>
      <SourcesPage />
    </MemoryRouter>,
  );
}

/** Dosya seçiciye verilen dosyaları bırakır. */
function dropFiles(files: File[]) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files } });
}

/** Yükleme hook'unu verilen durumla taklit eder. */
function mockUploadState(state: { isPending?: boolean; error?: ApiError; data?: unknown }) {
  useUploadSourcesMock.mockReturnValue({
    mutate: mutateMock,
    isPending: state.isPending ?? false,
    isError: state.error !== undefined,
    error: state.error ?? null,
    data: state.data ?? null,
  });
}

/** Belirtilen ad ve türle dosya üretir. */
function createFile(name: string, type: string) {
  return new File(["içerik"], name, { type });
}

afterEach(cleanup);

describe("SourcesPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    useMeMock.mockReturnValue({ data: contentManager, isPending: false });
    useSourcesMock.mockReturnValue({
      data: { items: [], page: 0, size: 20, total: 0 },
      isPending: false,
    });
    mockUploadState({});
  });

  test("yetkisi sunucudan gelen yöneticiye yükleme alanını gösterir", () => {
    renderSourcesPage();

    expect(document.title).toBe("İçerik yükle · Bilig");
    expect(screen.getByText("PDF'leri buraya bırak")).toBeInTheDocument();
  });

  test("içerik yetkisi olmayan kullanıcıya erişim engeli gösterir", () => {
    useMeMock.mockReturnValue({
      data: { ...contentManager, role: "STUDENT", canManageContent: false },
      isPending: false,
    });

    renderSourcesPage();

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Bu ekranı yalnızca içerik yöneticileri görüntüleyebilir.",
    );
    expect(screen.queryByText("PDF'leri buraya bırak")).not.toBeInTheDocument();
  });

  test("sadece PDF olmayan dosya bırakılırsa istek atmadan adıyla uyarır", async () => {
    renderSourcesPage();

    dropFiles([createFile("notlar.txt", "text/plain")]);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "PDF olmadığı için yüklenmeyen dosyalar: notlar.txt",
    );
    expect(mutateMock).not.toHaveBeenCalled();
  });

  test("karışık bırakmada PDF'leri yükler, diğerlerini adıyla bildirir", async () => {
    const pdf = createFile("kitap.pdf", "application/pdf");
    renderSourcesPage();

    dropFiles([pdf, createFile("tablo.docx", "application/msword")]);

    await waitFor(() => expect(mutateMock).toHaveBeenCalledWith([pdf]));
    expect(screen.getByRole("alert")).toHaveTextContent("tablo.docx");
  });

  test("birden çok PDF'i tek istekte gönderir", async () => {
    const firstPdf = createFile("kitap1.pdf", "application/pdf");
    const secondPdf = createFile("kitap2.pdf", "application/pdf");
    renderSourcesPage();

    dropFiles([firstPdf, secondPdf]);

    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(1));
    expect(mutateMock).toHaveBeenCalledWith([firstPdf, secondPdf]);
  });

  test("her dosyanın sonucunu ve daha önce yüklenmiş uyarısını gösterir", () => {
    mockUploadState({
      data: {
        files: [
          { sourceId: 101, fileName: "yeni.pdf", duplicate: false },
          { sourceId: 102, fileName: "eski.pdf", duplicate: true },
        ],
      },
    });

    renderSourcesPage();

    const rows = screen.getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("yeni.pdfYüklendi");
    expect(rows[1]).toHaveTextContent("eski.pdfBu dosya daha önce yüklenmiş");
  });

  test("sunucu hatasının mesajını gösterir", () => {
    mockUploadState({
      error: new ApiError(
        { code: "FILE_TOO_LARGE", detail: "Dosya en fazla 100 MB olabilir." },
        413,
      ),
    });

    renderSourcesPage();

    expect(screen.getByRole("alert")).toHaveTextContent("Dosya en fazla 100 MB olabilir.");
  });

  test("yükleme sürerken düğmeyi kapatır ve durumu gösterir", () => {
    mockUploadState({ isPending: true });

    renderSourcesPage();

    expect(screen.getByRole("button", { name: "Yükleniyor..." })).toBeDisabled();
  });
});
