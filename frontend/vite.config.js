import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,  // if 5173 taken, fall to 5174/5175 — all whitelisted in backend CORS
  },
})
