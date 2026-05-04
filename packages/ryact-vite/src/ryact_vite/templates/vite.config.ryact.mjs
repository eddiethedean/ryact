import { defineConfig } from "vite";

/** Minimal Ryact-oriented starter; merge into your app or rename to vite.config.mjs. */
export default defineConfig({
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
