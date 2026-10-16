import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // GitHub Pages project sites are served from /<repo-name>/, not the
  // domain root, so every built asset URL needs that prefix baked in.
  base: '/ATAST-JOURNEE-INTEGRATION-HOSTGAMEWEBSITE/',
  plugins: [react()],
  server: { port: 5173, open: '/' },
  preview: { port: 4173 },
});
