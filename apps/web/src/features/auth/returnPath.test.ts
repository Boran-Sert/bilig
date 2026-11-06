/**
 * Girişten sonra dönülecek adresin seçimini test eder.
 */
import { expect, test } from "vitest";
import { getReturnPath } from "./returnPath";

test("durum yoksa ana sayfayı döndürür", () => {
  expect(getReturnPath(null)).toBe("/panel");
});

test("uygulama içi adresi sorgusuyla döndürür", () => {
  expect(getReturnPath({ from: { pathname: "/sessions", search: "?page=2" } })).toBe(
    "/sessions?page=2",
  );
});

test("başka siteye giden adresi reddeder", () => {
  expect(getReturnPath({ from: { pathname: "//evil.example" } })).toBe("/panel");
});
