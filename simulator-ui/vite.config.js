import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
  ],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/state': 'http://localhost:7860',
      '/reset': 'http://localhost:7860',
      '/curriculum': 'http://localhost:7860',
      '/run-demo': 'http://localhost:7860',
      '/agent-logs': 'http://localhost:7860',
      '/demo-status': 'http://localhost:7860',
    },
  },
});
