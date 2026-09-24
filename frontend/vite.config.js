import { defineConfig } from 'vite';

export default defineConfig({
  build: { outDir: '../admin_dist', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/brand-font': 'http://127.0.0.1:8000' } },
});
