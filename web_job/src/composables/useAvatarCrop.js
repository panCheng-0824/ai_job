import { ref } from "vue";

const cropOpen = ref(false);
const cropImageSrc = ref("");

/** @type {{ resolve: (v: string) => void; reject: (e: Error) => void } | null} */
let pending = null;

/** 打开裁切弹窗，确认后 resolve 裁切后的 data URL */
export function openAvatarCrop(imageSrc) {
  return new Promise((resolve, reject) => {
    if (!imageSrc) {
      reject(new Error("无效图片"));
      return;
    }
    pending = { resolve, reject };
    cropImageSrc.value = imageSrc;
    cropOpen.value = true;
  });
}

export function confirmAvatarCrop(dataUrl) {
  cropOpen.value = false;
  cropImageSrc.value = "";
  pending?.resolve(dataUrl);
  pending = null;
}

export function cancelAvatarCrop() {
  cropOpen.value = false;
  cropImageSrc.value = "";
  pending?.reject(new Error("已取消裁切"));
  pending = null;
}

export function useAvatarCrop() {
  return {
    cropOpen,
    cropImageSrc,
    openAvatarCrop,
    confirmAvatarCrop,
    cancelAvatarCrop
  };
}
