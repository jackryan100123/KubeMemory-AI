import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target: env.VITE_API_URL?.replace(/\/api\/?$/, '') || 'http://localhost:8000', changeOrigin: true },
        '/ws': { target: env.VITE_WS_URL?.replace(/^wss?:\/\//, 'http://').replace(/\/ws\/?$/, '') || 'http://localhost:8000', ws: true, changeOrigin: true },
      }
    }
  }
})
