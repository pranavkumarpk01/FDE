import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api calls are forwarded to the Python backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: { "/api": process.env.VITE_API_TARGET || "http://localhost:8000" },
  },
});
