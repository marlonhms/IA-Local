import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    outDir: "../web/dist",
    emptyOutDir: true,
    minify: "esbuild",
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, "src/main.ts"),
      name: "AuraSDK",
      fileName: (format) => `aura-sdk.${format}.js`,
      formats: ["es", "umd"],
    },
    rollupOptions: {
      treeshake: true,
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/metrics": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
