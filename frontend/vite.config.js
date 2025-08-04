import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    // Make environment variables available to the app
    'process.env': process.env
  },
  build: {
    // Ensure environment variables are properly injected
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
