import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],   // ← BEZ tailwindcss()

  server: {
    port: 5173,
    proxy: {
      "/calculator": { target: "http://localhost:8000", changeOrigin: true },
      "/calculate":  { target: "http://localhost:8000", changeOrigin: true },
      "/report":     { target: "http://localhost:8000", changeOrigin: true },
      "/api":        { target: "http://localhost:8000", changeOrigin: true },
      "/webhooks":   { target: "http://localhost:8000", changeOrigin: true },
    },
  },

  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react":  ["react", "react-dom", "react-router-dom"],
          "vendor-charts": ["recharts"],
          "vendor-icons":  ["lucide-react"],
          "vendor-axios":  ["axios"],
        },
      },
    },
    chunkSizeWarningLimit: 800,
  },
});