<script setup>
/**
 * 岗位 ID 标签：点击展示岗位编号浮层（Teleport 到 body，避免被详情面板裁切）。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  jobId: { type: [String, Number], default: "" },
  label: { type: String, default: "JOB ID" },
  size: { type: String, default: "compact" }
});

const emit = defineEmits(["click"]);

const rootRef = ref(null);
const pillRef = ref(null);
const open = ref(false);
const copied = ref(false);
const popoverStyle = ref({ top: "0px", left: "0px", transform: "none" });
const placement = ref("bottom");

const displayId = computed(() => String(props.jobId ?? "").trim());
const hasId = computed(() => Boolean(displayId.value));

let copiedTimer = null;

function updatePosition() {
  const el = pillRef.value;
  if (!el || typeof window === "undefined") return;

  const rect = el.getBoundingClientRect();
  const popoverWidth = 300;
  const gap = 10;
  const left = Math.max(12, Math.min(rect.left, window.innerWidth - popoverWidth - 12));
  const spaceBelow = window.innerHeight - rect.bottom;
  const spaceAbove = rect.top;
  const showBelow = spaceBelow >= 96 || spaceBelow >= spaceAbove;

  placement.value = showBelow ? "bottom" : "top";
  popoverStyle.value = {
    top: showBelow ? `${rect.bottom + gap}px` : `${rect.top - gap}px`,
    left: `${left}px`,
    transform: showBelow ? "none" : "translateY(-100%)"
  };
}

function closePopover() {
  open.value = false;
  copied.value = false;
}

function togglePopover(ev) {
  ev?.stopPropagation?.();
  emit("click", ev);
  open.value = !open.value;
  if (open.value) {
    nextTick(updatePosition);
  } else {
    copied.value = false;
  }
}

async function copyId() {
  if (!displayId.value) return;
  try {
    await navigator.clipboard.writeText(displayId.value);
    copied.value = true;
    if (copiedTimer) clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => {
      copied.value = false;
    }, 1600);
  } catch {
    window.prompt("复制岗位编号", displayId.value);
  }
}

function onDocumentPointerDown(ev) {
  if (!open.value) return;
  const root = rootRef.value;
  const target = ev.target;
  if (root?.contains(target)) return;
  if (target?.closest?.(".job-id-popover")) return;
  closePopover();
}

function onDocumentKeydown(ev) {
  if (ev.key === "Escape" && open.value) closePopover();
}

function onWindowChange() {
  if (open.value) updatePosition();
}

watch(open, (isOpen) => {
  if (typeof document === "undefined") return;
  if (isOpen) {
    document.addEventListener("pointerdown", onDocumentPointerDown, true);
    document.addEventListener("keydown", onDocumentKeydown);
    window.addEventListener("resize", onWindowChange);
    window.addEventListener("scroll", onWindowChange, true);
  } else {
    document.removeEventListener("pointerdown", onDocumentPointerDown, true);
    document.removeEventListener("keydown", onDocumentKeydown);
    window.removeEventListener("resize", onWindowChange);
    window.removeEventListener("scroll", onWindowChange, true);
  }
});

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer);
  document.removeEventListener("pointerdown", onDocumentPointerDown, true);
  document.removeEventListener("keydown", onDocumentKeydown);
  window.removeEventListener("resize", onWindowChange);
  window.removeEventListener("scroll", onWindowChange, true);
});
</script>

<template>
  <span
    v-if="hasId"
    ref="rootRef"
    class="job-id-tag"
    :class="[`job-id-tag--${size}`, { 'job-id-tag--open': open }]"
  >
    <button
      ref="pillRef"
      type="button"
      class="job-id-tag__pill"
      :aria-expanded="open"
      :aria-label="`岗位编号 ${displayId}`"
      @click="togglePopover"
    >
      {{ label }}
    </button>

    <Teleport to="body">
      <Transition name="job-id-pop">
        <div
          v-if="open"
          class="job-id-popover"
          :class="`job-id-popover--${placement}`"
          :style="popoverStyle"
          role="dialog"
          aria-label="岗位编号"
          @click.stop
        >
          <div class="job-id-popover__head">
            <span class="job-id-popover__title">岗位编号</span>
            <button type="button" class="job-id-popover__close" aria-label="关闭" @click="closePopover">×</button>
          </div>
          <div class="job-id-popover__body">
            <code class="job-id-popover__code">{{ displayId }}</code>
          </div>
          <div class="job-id-popover__foot">
            <button type="button" class="job-id-popover__copy" @click="copyId">
              {{ copied ? "已复制" : "复制编号" }}
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </span>
</template>

<style scoped>
.job-id-tag {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.job-id-tag__pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  cursor: pointer;
  user-select: none;
  line-height: 1.4;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.job-id-tag--inline .job-id-tag__pill {
  font-size: 0.68rem;
  padding: 3px 10px;
}

.job-id-tag__pill:hover,
.job-id-tag--open .job-id-tag__pill {
  background: #e0e7ff;
  border-color: #a5b4fc;
}

.job-id-tag__pill:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.job-id-popover {
  position: fixed;
  z-index: 14150;
  width: min(300px, calc(100vw - 24px));
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.16);
  overflow: hidden;
}

.job-id-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.job-id-popover__title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}

.job-id-popover__close {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.job-id-popover__close:hover {
  background: #f1f5f9;
  color: #334155;
}

.job-id-popover__body {
  padding: 12px;
}

.job-id-popover__code {
  display: block;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.5;
  word-break: break-all;
  white-space: pre-wrap;
}

.job-id-popover__foot {
  display: flex;
  justify-content: flex-end;
  padding: 0 12px 12px;
}

.job-id-popover__copy {
  padding: 7px 14px;
  border-radius: 8px;
  border: none;
  background: #5b6adf;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}

.job-id-popover__copy:hover {
  background: #4f46e5;
}

.job-id-pop-enter-active,
.job-id-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.job-id-pop-enter-from,
.job-id-pop-leave-to {
  opacity: 0;
  transform: translateY(6px) !important;
}

.job-id-popover--top.job-id-pop-enter-from,
.job-id-popover--top.job-id-pop-leave-to {
  transform: translateY(calc(-100% - 6px)) !important;
}
</style>
