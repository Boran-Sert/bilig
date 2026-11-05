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

const { useMeMock, useUploadSourcesMock, useSourcesMock, useAnswerKeysMock, mutateMock } =
  vi.hoisted(() => ({
    useMeMock: vi.fn(),
    useUploadSourcesMock: vi.fn(),
    useSourcesMock: vi.fn(),
    useAnswerKeysMock: vi.fn(),
    mutateMock: vi.fn(),
  }));

vi.mock("../../auth/api", () => ({
  useMe: useMeMock,
}));

vi.mock("../api", () => ({
  useUploadSources: useUploadSourcesMock,
  useSources: useSourcesMock,
  useAnswerKeys: useAnswerKeysMock,
  /** Yeniden işleme hook'unu boşta taklit eder. */
  useReprocessSource: () => ({ mutate: vi.fn(), isPending: false, isError: false, error: null }),
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

/** Kaynak türü seçimini yapar. */
function selectKind(kind: string) {
  fireEvent.change(screen.getByLabelText("Kaynak türü"), { target: { value: kind } });
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
    useAnswerKeysMock.mockReturnValue({ data: [] });
    useMeMock.mockReturnValue({ data: contentManager, isPending: false });
    useSourcesMock.mockReturnValue({
      data: { items: [], page: 0, size: 20, total: 0 },
      isPending: false,
      isSuccess: true,
      isError: false,
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
    expect(useSourcesMock).toHaveBeenCalledWith(false);
  });

  test("kaynak listesi alınamazsa boş liste yerine hata mesajını gösterir", () => {
    useSourcesMock.mockReturnValue({
      isPending: false,
      isSuccess: false,
      isError: true,
      error: new ApiError({ code: "INTERNAL_ERROR", detail: "Kaynaklar okunamadı." }, 500),
    });

    renderSourcesPage();

    expect(screen.getByRole("alert")).toHaveTextContent("Kaynaklar okunamadı.");
    expect(screen.queryByText("Henüz yüklenmiş bir kaynak bulunmuyor.")).not.toBeInTheDocument();
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
    selectKind("TEXTBOOK");

    dropFiles([pdf, createFile("tablo.docx", "application/msword")]);

    await waitFor(() =>
      expect(mutateMock).toHaveBeenCalledWith({ files: [pdf], kind: "TEXTBOOK" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("tablo.docx");
  });

  test("birden çok PDF'i tek istekte gönderir", async () => {
    const firstPdf = createFile("kitap1.pdf", "application/pdf");
    const secondPdf = createFile("kitap2.pdf", "application/pdf");
    renderSourcesPage();
    selectKind("TEST");

    dropFiles([firstPdf, secondPdf]);

    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(1));
    expect(mutateMock).toHaveBeenCalledWith({ files: [firstPdf, secondPdf], kind: "TEST" });
  });

  test("teste seçilen cevap anahtarını yüklemeyle gönderir", async () => {
    useAnswerKeysMock.mockReturnValue({
      data: [{ sourceId: 7, fileName: "CEVAP_ANAHTARI.pdf", kind: "ANSWER_KEY" }],
    });
    const pdf = createFile("14.pdf", "application/pdf");
    renderSourcesPage();
    selectKind("TEST");
    fireEvent.change(screen.getByLabelText("Cevap anahtarı"), { target: { value: "7" } });

    dropFiles([pdf]);

    await waitFor(() =>
      expect(mutateMock).toHaveBeenCalledWith({ files: [pdf], kind: "TEST", answerKeySourceId: 7 }),
    );
  });

  test("tür seçilmeden bırakılan PDF'i yüklemez ve tür seçmeyi ister", async () => {
    renderSourcesPage();

    dropFiles([createFile("kitap.pdf", "application/pdf")]);

    expect(await screen.findByRole("alert")).toHaveTextContent("Önce kaynağın türünü seç.");
    expect(mutateMock).not.toHaveBeenCalled();
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
