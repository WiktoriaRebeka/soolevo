// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // W trybie dev proxy API do lokalnego backendu
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/calculate': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/report': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/webhooks': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,  // wyłącz na produkcji
    rollupOptions: {
      output: {
        // Chunki z hashem — długi cache w przeglądarce
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
        // Osobne chunki dla dużych zależności
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'axios': ['axios'],
        },
      },
    },
  },
  define: {
    // Zmienna dostępna w kodzie React
    // Ustaw VITE_API_URL=https://api.soolevo.com w .env.production
  },
})
