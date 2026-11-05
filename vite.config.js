import { defineConfig } from "vite";
import { resolve } from "path";

/**
 * StoryBook Studio — Vite Configuration
 * - Supports HMR development proxy to FastAPI backend (http://127.0.0.1:8000)
 * - Builds standalone ES Module & Web Component bundle (<storybook-dtp-spread>)
 * - Preserves 100% direct execution compatibility with `python run_web.py` (시집만들기.bat)
 */
export default defineConfig({
  root: "web/static",
  base: "/static/",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/projects": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: resolve(__dirname, "dist"),
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "web/static/js/main.esm.js"),
      name: "StoryBookStudio",
      formats: ["es", "umd"],
      fileName: (format) => `storybook-studio.${format}.js`,
    },
  },
});

