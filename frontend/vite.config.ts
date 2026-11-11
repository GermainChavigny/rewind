import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

// In dev, the backend (`rewind serve`, port 8080) answers /api and /media.
const backend = process.env.REWIND_BACKEND ?? 'http://localhost:8080';

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    proxy: { '/api': backend, '/media': backend },
  },
  build: { target: 'es2022', assetsInlineLimit: 0 },
  test: { include: ['src/**/*.test.ts'] },
});
