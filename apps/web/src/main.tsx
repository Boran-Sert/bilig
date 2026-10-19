/**
 * Arayüzün giriş noktası.
 * Uygulamayı index.html içindeki root elemanına bağlar.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <main />
  </StrictMode>,
);
