// vite.config.js
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    target: "esnext",
    outDir: "dist",
  },
  optimizeDeps: {
    esbuildOptions: {
      target: "esnext",
    },
  },
});