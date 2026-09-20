import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/media": { target: "http://127.0.0.1:8000", timeout: 0, proxyTimeout: 0 },
      "/projects": "http://127.0.0.1:8000",
      "/notes": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
