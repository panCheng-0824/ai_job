<script setup>
import { computed } from "vue";
import ResumeExportMenu from "./ResumeExportMenu.vue";
import { stripTimeCopySuffix } from "../../modules/resume/storage";

const props = defineProps({
  activeSeries: { type: Object, default: null },
  resumeGroups: { type: Array, default: () => [] },
  seriesId: { type: String, default: null },
  draftId: { type: String, default: null },
  saving: { type: Boolean, default: false },
  canSaveInPlace: { type: Boolean, default: false },
  accent: { type: String, default: "#5b6adf" }
});

const emit = defineEmits([
  "load-version",
  "delete-version",
  "save-as-copy",
  "save-draft",
  "export",
  "select-group"
]);

const versionHistory = computed(() => {
  const list = [...(props.activeSeries?.versions || [])];
  return list.sort((a, b) => (b.updatedAt || b.createdAt || 0) - (a.updatedAt || a.createdAt || 0));
});

function formatTime(rec) {
  const n = rec?.updatedAt || rec?.createdAt;
  if (!n) return "";
  const d = new Date(n);
  const pad = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function versionLabel(rec) {
  const full = String(rec?.displayName || "").trim();
  if (/_\d{14}$/.test(full)) {
    return full;
  }
  return stripTimeCopySuffix(full) || "未命名简历";
}

function isSnapshot(rec) {
  return /_\d{14}$/.test(String(rec?.displayName || ""));
}
</script>

<template>
  <div class="version-preview-panel">
    <section v-if="resumeGroups.length" class="vpp-section">
      <h3 class="vpp-section-title">全部简历</h3>
      <ul class="vpp-resume-list">
        <li
          v-for="g in resumeGroups"
          :key="g.seriesId"
          class="vpp-resume-item"
          :class="{ active: g.seriesId === seriesId }"
          :style="{ '--vpp-accent': accent }"
        >
          <button type="button" class="vpp-resume-btn" @click="emit('select-group', g)">
            <span class="vpp-resume-name">{{ g.label }}</span>
            <span class="vpp-resume-meta">{{ g.versions.length }} 个版本</span>
          </button>
        </li>
      </ul>
    </section>

    <section class="vpp-section">
      <h3 class="vpp-section-title">版本历史</h3>
      <p v-if="!versionHistory.length" class="vpp-empty">暂无版本记录，保存后将出现在此。</p>

      <ul v-else class="vpp-list">
        <li
          v-for="rec in versionHistory"
          :key="rec.id"
          class="vpp-item"
          :class="{ active: rec.id === draftId }"
          :style="{ '--vpp-accent': accent }"
        >
          <button type="button" class="vpp-item-main" @click="emit('load-version', rec)">
            <span class="vpp-item-name">
              {{ versionLabel(rec) }}
              <span v-if="isSnapshot(rec)" class="vpp-item-tag">快照</span>
              <span v-else-if="rec.isSeriesDefault" class="vpp-item-tag vpp-item-tag--current">当前</span>
            </span>
            <span class="vpp-item-time">{{ formatTime(rec) }}</span>
          </button>
          <div class="vpp-item-actions">
            <ResumeExportMenu
              compact
              label="↓"
              :formats="['pdf', 'docx', 'json']"
              @export="(format) => emit('export', { format, record: rec })"
            />
            <button
              type="button"
              class="vpp-icon-btn vpp-icon-btn--danger"
              title="删除"
              @click="emit('delete-version', rec.id)"
            >
              ×
            </button>
          </div>
        </li>
      </ul>
    </section>

    <div class="vpp-footer">
      <button
        type="button"
        class="vpp-btn vpp-btn--ghost"
        :disabled="saving"
        @click="emit('save-draft')"
      >
        {{ canSaveInPlace ? "保存" : "保存并创建" }}
      </button>
      <button
        type="button"
        class="vpp-btn vpp-btn--outline"
        :disabled="saving"
        @click="emit('save-as-copy')"
      >
        另存为新简历
      </button>
    </div>
  </div>
</template>

<style scoped>
.version-preview-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  --vpp-accent: #5b6adf;
}
.vpp-section-title {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.vpp-resume-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.vpp-resume-item {
  border: 1px solid #e8ecf4;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.vpp-resume-item.active {
  border-color: var(--vpp-accent, #5b6adf);
  background: #f5f7ff;
}
.vpp-resume-btn {
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.vpp-resume-name {
  display: block;
  font-size: 0.82rem;
  font-weight: 700;
  color: #1e293b;
}
.vpp-resume-meta {
  display: block;
  margin-top: 2px;
  font-size: 0.72rem;
  color: #94a3b8;
}
.vpp-empty {
  margin: 0;
  padding: 16px 8px;
  text-align: center;
  font-size: 0.82rem;
  color: #94a3b8;
}
.vpp-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: min(360px, 48vh);
  overflow: auto;
}
.vpp-item {
  display: flex;
  align-items: stretch;
  gap: 6px;
  border: 1px solid #e8ecf4;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.vpp-item.active {
  border-color: var(--vpp-accent, #5b6adf);
  background: #f5f7ff;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--vpp-accent, #5b6adf) 20%, transparent);
}
.vpp-item-main {
  flex: 1;
  min-width: 0;
  text-align: left;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.vpp-item-main:hover {
  background: #f8fafc;
}
.vpp-item-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vpp-item-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 600;
  color: #64748b;
  background: #f1f5f9;
}
.vpp-item-tag--current {
  color: var(--vpp-accent, #5b6adf);
  background: #eef2ff;
}
.vpp-item-time {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: #94a3b8;
}
.vpp-item-actions {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 6px 8px 6px 0;
}
.vpp-item-actions :deep(.resume-export-trigger--compact) {
  width: 28px;
  height: 28px;
  min-width: 28px;
  padding: 0;
  border-radius: 8px;
  font-size: 0.85rem;
}
.vpp-item-actions :deep(.resume-export-caret) {
  display: none;
}
.vpp-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 0.85rem;
  cursor: pointer;
  line-height: 1;
}
.vpp-icon-btn:hover {
  border-color: #c7d2fe;
  color: #5b6adf;
}
.vpp-icon-btn--danger:hover {
  border-color: #fecaca;
  color: #dc2626;
}
.vpp-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}
.vpp-btn {
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.vpp-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.vpp-btn--outline {
  border: 1px solid var(--vpp-accent, #5b6adf);
  background: #fff;
  color: var(--vpp-accent, #5b6adf);
}
.vpp-btn--outline:hover:not(:disabled) {
  background: #eef2ff;
}
.vpp-btn--ghost {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
}
.vpp-btn--ghost:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: #5b6adf;
}
</style>
