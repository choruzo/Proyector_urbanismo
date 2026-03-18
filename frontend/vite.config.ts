import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // En Docker: el servicio backend se llama "backend" en la red interna.
        // En desarrollo local fuera de Docker: cambiar a http://localhost:8001
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
