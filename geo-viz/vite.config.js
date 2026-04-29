import { defineConfig } from 'vite';

export default defineConfig({
  base: '/geospatial-vision/geo-viz/',
  build: {
    outDir: 'dist',
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          deckgl:   ['deck.gl'],
          cogtools: ['geotiff', 'geotiff-geokeys-to-proj4', 'proj4'],
        },
      },
    },
  },
});
