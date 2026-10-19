/**
 * Vite ayarları.
 * Geliştirirken /api isteklerini yerelde çalışan Java servisine iletir.
 */
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8081",
    },
  },
});
