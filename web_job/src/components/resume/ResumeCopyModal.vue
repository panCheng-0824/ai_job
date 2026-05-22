<script setup>
import { onMounted, onUnmounted, watch } from "vue";
import { stripTimeCopySuffix } from "../../modules/resume/storage";

const props = defineProps({
  open: { type: Boolean, default: false },
  group: { type: Object, default: null },
  draftId: { type: String, default: null }
});

const emit = defineEmits(["close", "load", "set-default", "delete", "delete-series"]);

function formatTime(rec) {
  const n = rec?.updatedAt || rec?.createdAt;
  if (!n) return "";
  const d = new Date(n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function onKeydown(ev) {
  if (ev.key === "Escape" && props.open) emit("close");
}

function onRowClick(r, ev) {
  if (ev.target.closest("button")) return;
  emit("load", r);
}

watch(
  () => props.open,
  (open) => {
    document.body.style.overflow = open ? "hidden" : "";
  }
);

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && group"
      class="copy-modal-backdrop"
      role="presentation"
      @click.self="emit('close')"
    >
      <div
        class="copy-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="copy-modal-title"
        @click.stop
      >
        <header class="copy-modal-header">
          <div class="copy-modal-header-text">
            <h2 id="copy-modal-title">{{ stripTimeCopySuffix(group.label) }}</h2>
            <p class="copy-modal-sub">共 {{ group.versions?.length || 0 }} 条副本 · 点击行载入编辑</p>
          </div>
          <button type="button" class="copy-modal-close" aria-label="关闭" @click="emit('close')">×</button>
        </header>

        <div class="copy-modal-legend">
          <span class="pill pill-series">本简历默认</span>
          <span class="legend-text">打开该线时优先加载</span>
          <span class="pill pill-global">对话默认</span>
          <span class="legend-text">规划师拖入（全账号一条）</span>
        </div>

        <ul class="copy-modal-list">
          <li
            v-for="r in group.versions"
            :key="r.id"
            class="copy-modal-item"
            :class="{ active: r.id === draftId, 'is-editing': r.id === draftId }"
            @click="onRowClick(r, $event)"
          >
            <div class="copy-modal-item-main">
              <span class="copy-modal-time">{{ formatTime(r) }}</span>
              <div class="copy-modal-badges">
                <span v-if="r.id === draftId" class="pill pill-edit">编辑中</span>
                <span v-if="r.isSeriesDefault" class="pill pill-series">本简历默认</span>
                <span v-if="r.isDefault" class="pill pill-global">对话默认</span>
              </div>
            </div>
            <div class="copy-modal-item-actions">
              <button type="button" class="act act-primary" @click="emit('load', r)">载入</button>
              <button
                v-if="!r.isSeriesDefault"
                type="button"
                class="act"
                @click="emit('set-default', r.id, 'series')"
              >
                本线默认
              </button>
              <button
                v-if="!r.isDefault"
                type="button"
                class="act"
                @click="emit('set-default', r.id, 'global')"
              >
                对话默认
              </button>
              <button type="button" class="act act-danger" @click="emit('delete', r.id)">删除</button>
            </div>
          </li>
        </ul>

        <footer class="copy-modal-footer">
          <button type="button" class="btn-footer danger" @click="emit('delete-series', group)">
            删除整份简历（全部副本）
          </button>
          <button type="button" class="btn-footer ghost" @click="emit('close')">关闭</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.copy-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 14000;
  background: rgba(15, 23, 42, 0.52);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  overflow-y: auto;
}
.copy-modal {
  width: 100%;
  max-width: 560px;
  max-height: min(88vh, 720px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.28);
  overflow: hidden;
}
.copy-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 12px;
  border-bottom: 1px solid #eef2f6;
  background: linear-gradient(180deg, #fafbff, #fff);
  flex-shrink: 0;
}
.copy-modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
  color: #0f172a;
}
.copy-modal-sub {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: #64748b;
}
.copy-modal-close {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: #f1f5f9;
  color: #475569;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
}
.copy-modal-close:hover {
  background: #e2e8f0;
}
.copy-modal-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 10px 18px;
  background: #f8fafc;
  border-bottom: 1px solid #eef2f6;
  flex-shrink: 0;
}
.legend-text {
  font-size: 0.75rem;
  color: #64748b;
}
.copy-modal-list {
  list-style: none;
  margin: 0;
  padding: 12px 14px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.copy-modal-item {
  border: 1px solid #e8ecf1;
  border-radius: 12px;
  padding: 12px 14px;
  background: #fcfcff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.copy-modal-item:hover {
  border-color: #c7d2fe;
  background: #f8faff;
}
.copy-modal-item.active {
  border-color: #6366f1;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.35);
  background: #f5f3ff;
}
.copy-modal-item-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.copy-modal-time {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  color: #334155;
  font-weight: 600;
}
.copy-modal-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.copy-modal-item-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.act {
  font-size: 0.78rem;
  padding: 5px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  font-weight: 500;
}
.act:hover {
  border-color: #a5b4fc;
  background: #f5f3ff;
}
.act-primary {
  border-color: #818cf8;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 600;
}
.act-danger {
  color: #dc2626;
  border-color: #fecaca;
  background: #fff;
}
.act-danger:hover {
  background: #fef2f2;
}
.copy-modal-footer {
  display: flex;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid #eef2f6;
  background: #fafbfc;
  flex-shrink: 0;
}
.btn-footer {
  flex: 1;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #d1d5db;
  background: #fff;
}
.btn-footer.ghost {
  flex: 0 0 auto;
  min-width: 88px;
}
.btn-footer.danger {
  color: #dc2626;
  border-color: #fecaca;
  background: #fff;
}
.btn-footer.danger:hover {
  background: #fef2f2;
}
.pill {
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.pill-series {
  background: #e0e7ff;
  color: #4338ca;
}
.pill-global {
  background: #fef3c7;
  color: #b45309;
}
.pill-edit {
  background: #dbeafe;
  color: #1d4ed8;
}
</style>
