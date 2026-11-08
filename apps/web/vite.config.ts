import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
// Backend chạy bằng: .venv\Scripts\python -m tutor_backend serve (cổng 8000)
const backendUrl = process.env.TUTOR_BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Lược đồ kịch bản là hợp đồng chung của 3 app: Web đọc thẳng từ schemas/, không chép
      "@schemas": `${repoRoot}schemas`,
    },
  },
  server: {
    port: 5173,
    proxy: { "/api": backendUrl },
    fs: { allow: [repoRoot] },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
