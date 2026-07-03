const VIEWPORT_SIZE = 240;
const OUTPUT_SIZE = 256;

/** 读取原图 data URL（裁切前不做缩放） */
export function readImageFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file?.type?.startsWith("image/")) {
      reject(new Error("请选择图片文件"));
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.onload = () => resolve(String(reader.result || ""));
    reader.readAsDataURL(file);
  });
}

/** 加载 data URL 为 HTMLImageElement */
export function loadImageFromDataUrl(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onerror = () => reject(new Error("图片格式无效"));
    img.onload = () => resolve(img);
    img.src = dataUrl;
  });
}

/** 计算铺满圆形视口的初始缩放（cover） */
export function computeAvatarCoverScale(img, viewportSize = VIEWPORT_SIZE) {
  return Math.max(viewportSize / Math.max(img.width, 1), viewportSize / Math.max(img.height, 1));
}

/**
 * 按视口内的平移/缩放导出圆形头像 JPEG。
 * panX/panY：相对视口中心的像素偏移；scale：在 cover 基准上的倍率。
 */
export function exportCircularAvatarCrop(
  img,
  { panX = 0, panY = 0, scale = 1, viewportSize = VIEWPORT_SIZE, outputSize = OUTPUT_SIZE, quality = 0.88 } = {}
) {
  const cover = computeAvatarCoverScale(img, viewportSize);
  const drawScale = cover * scale;
  const ratio = outputSize / viewportSize;

  const canvas = document.createElement("canvas");
  canvas.width = outputSize;
  canvas.height = outputSize;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("无法处理图片");

  ctx.beginPath();
  ctx.arc(outputSize / 2, outputSize / 2, outputSize / 2, 0, Math.PI * 2);
  ctx.closePath();
  ctx.clip();

  const drawW = img.width * drawScale * ratio;
  const drawH = img.height * drawScale * ratio;
  const dx = outputSize / 2 + panX * ratio - drawW / 2;
  const dy = outputSize / 2 + panY * ratio - drawH / 2;
  ctx.drawImage(img, dx, dy, drawW, drawH);
  return canvas.toDataURL("image/jpeg", quality);
}

/** 将图片文件压缩为 JPEG data URL（无裁切，兼容旧逻辑） */
export function readImageAsDataUrl(file, { maxEdge = 256, quality = 0.82 } = {}) {
  return new Promise((resolve, reject) => {
    if (!file?.type?.startsWith("image/")) {
      reject(new Error("请选择图片文件"));
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("图片格式无效"));
      img.onload = () => {
        try {
          const scale = Math.min(1, maxEdge / Math.max(img.width, img.height, 1));
          const w = Math.max(1, Math.round(img.width * scale));
          const h = Math.max(1, Math.round(img.height * scale));
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext("2d");
          if (!ctx) {
            reject(new Error("无法处理图片"));
            return;
          }
          ctx.drawImage(img, 0, 0, w, h);
          resolve(canvas.toDataURL("image/jpeg", quality));
        } catch (e) {
          reject(e);
        }
      };
      img.src = String(reader.result || "");
    };
    reader.readAsDataURL(file);
  });
}

export { VIEWPORT_SIZE, OUTPUT_SIZE };
