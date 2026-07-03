<script setup>
/**
 * 学生头像：有图显示照片，无图显示姓名/学号占位；editable 时可点击上传。
 */
import { computed, onMounted, ref, watch } from "vue";
import { avatarFallbackText, resolveStudentAvatarUrl, setStudentServerAvatar, useStudentAvatar } from "../../composables/useStudentAvatar";
import { openAvatarCrop } from "../../composables/useAvatarCrop";
import { readImageFileAsDataUrl } from "../../utils/avatarImage";

const props = defineProps({
  name: { type: String, default: "" },
  studentId: { type: String, default: "" },
  /** xs | sm | md | lg | xl | fill（铺满父容器） */
  size: { type: String, default: "md" },
  /** 侧栏等深色底：占位字浅色 */
  tone: { type: String, default: "warm" },
  /** 服务端头像 URL，优先于本地缓存 */
  imageUrl: { type: String, default: "" },
  editable: { type: Boolean, default: false },
  /** 若提供，选图裁切后上传至服务端（MinIO）而非仅 localStorage */
  uploadHandler: { type: Function, default: null },
  title: { type: String, default: "" }
});

const emit = defineEmits(["change"]);

const { syncFromStorage, setAvatarFromFile } = useStudentAvatar();
const fileInputRef = ref(null);

const fallback = computed(() => avatarFallbackText(props.name, props.studentId));
const displayUrl = computed(() => props.imageUrl?.trim() || resolveStudentAvatarUrl(props.studentId));
const ariaLabel = computed(() => props.title || (props.editable ? "修改头像" : "头像"));

function refresh() {
  syncFromStorage(props.studentId);
}

onMounted(refresh);
watch(() => props.studentId, refresh);

function openPicker() {
  if (!props.editable) return;
  fileInputRef.value?.click();
}

async function dataUrlToFile(dataUrl, filename = "avatar.jpg") {
  const resp = await fetch(dataUrl);
  const blob = await resp.blob();
  return new File([blob], filename, { type: blob.type || "image/jpeg" });
}

async function onFileChange(ev) {
  const file = ev.target?.files?.[0];
  if (!file) return;
  try {
    if (props.uploadHandler) {
      const raw = await readImageFileAsDataUrl(file);
      let cropped;
      try {
        cropped = await openAvatarCrop(raw);
      } catch (e) {
        if (String(e?.message || "").includes("取消")) return;
        throw e;
      }
      const uploadFile = await dataUrlToFile(cropped, `avatar-${props.studentId || "user"}.jpg`);
      const url = await props.uploadHandler(uploadFile);
      if (url) {
        setStudentServerAvatar(url, props.studentId);
        emit("change", url);
      }
      return;
    }
    const url = await setAvatarFromFile(file, props.studentId);
    if (url) emit("change", url);
  } catch (e) {
    window.alert(e?.message || "上传头像失败");
  } finally {
    ev.target.value = "";
  }
}
</script>

<template>
  <component
    :is="editable ? 'button' : 'span'"
    type="button"
    class="student-avatar"
    :class="[
      size === 'fill' ? 'student-avatar--fill' : `student-avatar--${size}`,
      `student-avatar--tone-${tone}`,
      { 'student-avatar--editable': editable }
    ]"
    :title="ariaLabel"
    :aria-label="ariaLabel"
    @click="openPicker"
  >
    <img v-if="displayUrl" :src="displayUrl" alt="" class="student-avatar-img" />
    <span v-else class="student-avatar-fallback">{{ fallback }}</span>
    <input
      v-if="editable"
      ref="fileInputRef"
      type="file"
      accept="image/*"
      class="student-avatar-input"
      tabindex="-1"
      aria-hidden="true"
      @change="onFileChange"
    />
  </component>
</template>

<style scoped>
.student-avatar {
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: none;
  padding: 0;
  margin: 0;
  font-weight: 800;
  line-height: 1;
  box-sizing: border-box;
}
.student-avatar--editable {
  cursor: pointer;
  transition: box-shadow 0.18s, transform 0.18s;
}
.student-avatar--editable:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15);
}
.student-avatar--xs {
  width: 28px;
  height: 28px;
  font-size: 0.62rem;
}
.student-avatar--sm {
  width: 38px;
  height: 38px;
  font-size: 0.68rem;
}
.student-avatar--md {
  width: 42px;
  height: 42px;
  font-size: 0.72rem;
}
.student-avatar--lg {
  width: 56px;
  height: 56px;
  font-size: 0.88rem;
}
.student-avatar--xl {
  width: 72px;
  height: 72px;
  font-size: 1.1rem;
}
.student-avatar--fill {
  width: 100%;
  height: 100%;
  font-size: 0.72rem;
}
.student-avatar--tone-warm {
  background: linear-gradient(135deg, #fde68a, #f59e0b);
  color: #78350f;
}
.student-avatar--tone-sidebar {
  background: linear-gradient(145deg, #fde68a, #f59e0b);
  color: #78350f;
}
.student-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.student-avatar-fallback {
  user-select: none;
}
.student-avatar-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
</style>
