/**
 * Uygulamanın giriş noktası.
 * Çevirileri, sayfa yönlendirmelerini ve sunucu durumu yönetimini başlatır.
 */
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { clearSessionOnUnauthorized } from "./features/auth/api";
import "./lib/i18n";
import { router } from "./routes";
import "./styles/index.css";

const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({
    /** Oturum düşerse kullanıcıyı girişe gönderir. */
    onError: (error) => clearSessionOnUnauthorized(queryClient, error),
  }),
  mutationCache: new MutationCache({
    /** Oturum düşerse kullanıcıyı girişe gönderir. */
    onError: (error) => clearSessionOnUnauthorized(queryClient, error),
  }),
});
const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element was not found.");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
