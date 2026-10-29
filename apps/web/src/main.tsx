/**
 * Uygulamanın giriş noktası.
 * Çevirileri ve sayfa yönlendirmelerini başlatıp React uygulamasını bağlar.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import "./lib/i18n";
import { router } from "./routes";
import "./styles/index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element was not found.");
}

createRoot(rootElement).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
