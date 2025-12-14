import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/arxiv': {
        target: 'https://export.arxiv.org/api/query',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/arxiv/, ''),
      },
    },
  },
})
