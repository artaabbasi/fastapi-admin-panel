import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  base: "/admin/",
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    outDir: "../fastapi_admin_panel/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/admin/api": "http://localhost:8000",
    },
  },
});
