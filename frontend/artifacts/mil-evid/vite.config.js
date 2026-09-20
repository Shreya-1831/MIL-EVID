import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    base: env.VITE_BASE_PATH || "/",
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": "/src",
      },
    },
    server: {
      host: "localhost",
      port: Number(env.VITE_PORT) || 5173,
    },
  };
});