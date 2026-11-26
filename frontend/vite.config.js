import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // forward API calls to the FastAPI server during development
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
