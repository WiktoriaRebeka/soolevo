// frontend/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    proxy: {
      // Endpointy kalkulatora
      "/calculator": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // Stare endpointy (kompatybilność wsteczna)
      "/calculate": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/report": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // Nowe moduły Soolevo
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/webhooks": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },

  build: {
    // Chunking — oddzielne bundle dla recharts i lucide
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-charts": ["recharts"],
          "vendor-icons": ["lucide-react"],
          "vendor-axios": ["axios"],
        },
      },
    },
    chunkSizeWarningLimit: 800,
  },

  // Zmienne środowiskowe
  // W dev: brak VITE_API_URL → proxy działa lokalnie
  // W produkcji .env.production: VITE_API_URL=https://api.soolevo.com
});