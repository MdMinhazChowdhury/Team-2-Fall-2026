import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  root: 'src/frontend',
  plugins: [react(), tailwindcss()],
  build: { outDir: '../../dist', emptyOutDir: true },
  server: {
    host: '127.0.0.1',
    proxy: { '^/api/(?!.*\\.(?:ts|tsx)(?:\\?|$))': 'http://127.0.0.1:8000' },
  },
  test: {
    root: '.',
    include: ['tests/frontend/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['tests/frontend/setup.ts'],
  },
});
