<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { RESUME_EXPORT_FORMAT_LABELS } from "../../modules/resume/exportDocument";

const props = defineProps({
  label: { type: String, default: "导出简历" },
  compact: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  formats: {
    type: Array,
    default: () => ["pdf", "docx", "json"]
  }
});

const emit = defineEmits(["export"]);

const open = ref(false);
const rootRef = ref(null);

function toggleMenu() {
  if (props.disabled) return;
  open.value = !open.value;
}

function pick(format) {
  open.value = false;
  emit("export", format);
}

function onDocumentClick(ev) {
  if (!open.value) return;
  const root = rootRef.value;
  if (root && !root.contains(ev.target)) {
    open.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
});
</script>

<template>
  <div ref="rootRef" class="resume-export-menu" :class="{ 'resume-export-menu--compact': compact }">
    <button
      type="button"
      class="resume-export-trigger"
      :class="{ 'resume-export-trigger--compact': compact, 'resume-export-trigger--open': open }"
      :disabled="disabled"
      :aria-expanded="open"
      aria-haspopup="menu"
      @click.stop="toggleMenu"
    >
      {{ label }}
      <span class="resume-export-caret" aria-hidden="true">▾</span>
    </button>
    <div v-if="open" class="resume-export-dropdown" role="menu" @click.stop>
      <button
        v-for="fmt in formats"
        :key="fmt"
        type="button"
        class="resume-export-item"
        role="menuitem"
        @click="pick(fmt)"
      >
        {{ RESUME_EXPORT_FORMAT_LABELS[fmt] || fmt }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.resume-export-menu {
  position: relative;
  display: inline-flex;
}
.resume-export-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 14px;
  min-width: 96px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  white-space: nowrap;
}
.resume-export-trigger--compact {
  min-width: 0;
  padding: 6px 10px;
  font-size: 0.72rem;
}
.resume-export-trigger:hover:not(:disabled),
.resume-export-trigger--open {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.resume-export-trigger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.resume-export-caret {
  font-size: 0.65rem;
  opacity: 0.75;
}
.resume-export-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 40;
  min-width: 120px;
  padding: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
}
.resume-export-menu--compact .resume-export-dropdown {
  right: auto;
  left: 0;
}
.resume-export-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}
.resume-export-item:hover {
  background: #eef2ff;
  color: var(--home-primary, #5b6adf);
}
</style>
