/**
 * İpucu hook'unun ipucunu iletmesini, hata saklamasını ve sıfırlanmasını test eder.
 * @vitest-environment jsdom
 */
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import "../../lib/i18n";
import { ApiError } from "../../lib/api/problem";
import { useQuestionHints } from "./useQuestionHints";

const { mutateMock, resetMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
  resetMock: vi.fn(),
}));

vi.mock("./api", () => ({
  /** Test için ipucu mutasyonunu sahte olarak sunar. */
  useHint: () => ({ mutate: mutateMock, reset: resetMock, isPending: false }),
}));

afterEach(cleanup);

describe("useQuestionHints", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    resetMock.mockReset();
  });

  test("gelen ipucunu çağıranın işlevine verir", () => {
    mutateMock.mockImplementation((_id, options) =>
      options.onSuccess({ hint: "Genel mesaja bak." }),
    );
    const onHint = vi.fn();
    const { result } = renderHook(() => useQuestionHints());

    act(() => result.current.requestHint(7, onHint));

    expect(mutateMock).toHaveBeenCalledWith(7, expect.any(Object));
    expect(onHint).toHaveBeenCalledWith("Genel mesaja bak.");
  });

  test("sunucu hatasında ipucu vermez ve hata metnini saklar", () => {
    mutateMock.mockImplementation((_id, options) =>
      options.onError(new ApiError({ code: "AI_UNAVAILABLE", detail: "Servis kapalı." }, 503)),
    );
    const onHint = vi.fn();
    const { result } = renderHook(() => useQuestionHints());

    act(() => result.current.requestHint(7, onHint));

    expect(onHint).not.toHaveBeenCalled();
    expect(result.current.error).toBe("Servis kapalı.");
  });

  test("sıfırlanınca hatayı temizler", () => {
    mutateMock.mockImplementation((_id, options) =>
      options.onError(new ApiError({ code: "AI_UNAVAILABLE", detail: "Servis kapalı." }, 503)),
    );
    const { result } = renderHook(() => useQuestionHints());
    act(() => result.current.requestHint(7, vi.fn()));

    act(() => result.current.reset());

    expect(result.current.error).toBeNull();
    expect(resetMock).toHaveBeenCalled();
  });
});
