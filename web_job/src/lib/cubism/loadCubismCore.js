/** 加载 Live2D Cubism Core（须在 import Framework 之前完成） */
export function loadCubismCoreScript() {
  if (typeof window !== "undefined" && window.Live2DCubismCore) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-cubism-core="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      if (window.Live2DCubismCore) resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = "/cubism/Core/live2dcubismcore.js";
    script.dataset.cubismCore = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Live2D Cubism Core 加载失败"));
    document.head.appendChild(script);
  });
}
