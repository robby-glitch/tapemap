import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Vite config — https://vitejs.dev/config/
// Dev server proxies /api to the Python TapeMap backend (no CORS on that server),
// so the browser talks same-origin and the proxy forwards to 127.0.0.1:8765.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
  // `vite preview` does NOT inherit server.proxy. Without this a built preview
  // silently serves index.html for /api and the app falls back to placeholder
  // data — which on a trading screen is worse than an outright error.
  preview: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
})
