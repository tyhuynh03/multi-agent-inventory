import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.INV_API_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
