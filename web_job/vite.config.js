import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const cubismRoot = path.resolve(__dirname, "../CubismSdkForWeb-5-r.5");

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@framework": path.join(cubismRoot, "Framework/src")
    }
  },
  server: {
    port: 5173,
    host: "0.0.0.0",
    fs: {
      allow: [__dirname, cubismRoot]
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true
      }
    }
  },
  optimizeDeps: {
    exclude: ["@framework"]
  }
});
