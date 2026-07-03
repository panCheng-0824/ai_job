/**
 * 将 Cubism SDK 运行时资源复制到 public/cubism（开发/构建前执行）
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const sdkRoot = path.resolve(root, "../CubismSdkForWeb-5-r.5");
const dst = path.join(root, "public/cubism");

const LIVE2D_MODELS = ["Haru", "Hiyori", "Mark", "Natori", "Rice", "Mao", "Wanko", "Ren"];

const copies = [
  { src: path.join(sdkRoot, "Core"), dst: path.join(dst, "Core") },
  {
    src: path.join(sdkRoot, "Framework/Shaders"),
    dst: path.join(dst, "Framework/Shaders")
  },
  ...LIVE2D_MODELS.map((model) => ({
    src: path.join(sdkRoot, "Samples/Resources", model),
    dst: path.join(dst, "Resources", model)
  }))
];

const files = [
  {
    src: path.join(sdkRoot, "Samples/Resources/back_class_normal.png"),
    dst: path.join(dst, "Resources/back_class_normal.png")
  },
  {
    src: path.join(sdkRoot, "Samples/Resources/icon_gear.png"),
    dst: path.join(dst, "Resources/icon_gear.png")
  }
];

function cpDir(src, target) {
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(src, target, { recursive: true });
}

if (!fs.existsSync(sdkRoot)) {
  console.warn("[copy-cubism] SDK not found:", sdkRoot);
  process.exit(0);
}

for (const item of copies) cpDir(item.src, item.dst);
for (const item of files) {
  fs.mkdirSync(path.dirname(item.dst), { recursive: true });
  fs.copyFileSync(item.src, item.dst);
}

console.log(`[copy-cubism] synced ${LIVE2D_MODELS.length} models to public/cubism`);
