/**
 * Vite yapılandırması.
 * React, Tailwind CSS ve yerel Java API proxy'sini ayarlar.
 */
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8081",
    },
  },
});
