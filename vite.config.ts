import { defineConfig } from 'vite'

export default defineConfig({
  root: 'web',
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3000'
    }
  },
  build: {
    outDir: '../dist/web',
    emptyOutDir: true
  }
})
