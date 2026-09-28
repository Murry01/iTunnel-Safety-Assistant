import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The /api proxy lets the frontend call your backend during development
// without CORS issues. Change the target to wherever your backend runs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
