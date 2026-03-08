import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/scenarios': 'http://localhost:8000',
      '/wargames': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
    }
  }
})
