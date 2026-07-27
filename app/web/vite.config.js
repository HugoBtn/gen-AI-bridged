import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The React dev server (5173) talks to the Python backend (8000) through this
// proxy, so the browser only ever calls same-origin /api/* — no CORS needed.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
