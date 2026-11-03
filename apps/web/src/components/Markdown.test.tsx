/**
 * Markdown bileşeninin altı çizili, tablo ve güvenli HTML davranışını test eder.
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import Markdown from "./Markdown";

afterEach(cleanup);

describe("Markdown", () => {
  test("altı çizili, italik ve kalın işaretlerini korur", () => {
    const { container } = render(
      <Markdown content={"Bu cümlede <u>altı çizili</u> sözcük, *Eylül* ve **kalın**"} />,
    );

    expect(container.querySelector("u")).toHaveTextContent("altı çizili");
    expect(container.querySelector("em")).toHaveTextContent("Eylül");
    expect(container.querySelector("strong")).toHaveTextContent("kalın");
  });

  test("GFM tablosunu tablo olarak gösterir", () => {
    const { container } = render(
      <Markdown content={"| Yazar | Eser |\n|---|---|\n| Mehmet Rauf | Eylül |"} />,
    );

    expect(container.querySelector("table")).toBeInTheDocument();
    expect(container.querySelectorAll("td")).toHaveLength(2);
  });

  test("izin verilmeyen HTML etiketlerini ve betikleri atar", () => {
    const { container } = render(
      <Markdown
        content={'<script>alert(1)</script><img src="x" onerror="alert(1)"><b>metin</b>'}
      />,
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(container).toHaveTextContent("metin");
    expect(container).not.toHaveTextContent("alert");
  });
});
