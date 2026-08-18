import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [vue()],
  build: {
    outDir: "bundle",
    emptyOutDir: true,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/assets": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/v1": "http://127.0.0.1:8000",
    },
  },
}));
