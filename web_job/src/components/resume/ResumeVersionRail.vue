<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { stripTimeCopySuffix } from "../../modules/resume/storage";

const VERSION_PANEL_STORAGE_KEY = "resume_version_default_panel_open";

const versionPanelOpen = ref(true);

onMounted(() => {
  try {
    const stored = localStorage.getItem(VERSION_PANEL_STORAGE_KEY);
    if (stored !== null) versionPanelOpen.value = stored === "1";
  } catch {
    /* ignore */
  }
});

watch(versionPanelOpen, (open) => {
  try {
    localStorage.setItem(VERSION_PANEL_STORAGE_KEY, open ? "1" : "0");
  } catch {
    /* ignore */
  }
});

function toggleVersionPanel() {
  versionPanelOpen.value = !versionPanelOpen.value;
}

const props = defineProps({
  resumeGroups: { type: Array, default: () => [] },
  seriesId: { type: String, default: null },
  draftId: { type: String, default: null },
  displayName: { type: String, default: "" },
  setAsGlobalDefault: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  canSaveInPlace: { type: Boolean, default: false },
  saveHint: { type: String, default: "" },
  hasStudentContext: { type: Boolean, default: false },
  studentId: { type: String, default: "" },
  globalDefaultId: { type: String, default: null },
  currentDraft: { type: Object, default: null },
  activeSeries: { type: Object, default: null },
  globalDefaultRecord: { type: Object, default: null },
  accent: { type: String, default: "#4f46e5" },
  panelTitle: { type: String, default: "版本与默认" }
});

const emit = defineEmits([
  "update:displayName",
  "update:setAsGlobalDefault",
  "save-draft",
  "save-as-copy",
  "new-series",
  "export-json",
  "select-group",
  "load-version",
  "set-default",
  "delete-version",
  "open-all-copies"
]);

const draftLabel = computed(() => {
  if (props.displayName?.trim()) return props.displayName.trim();
  if (props.currentDraft) return stripTimeCopySuffix(props.currentDraft.displayName || "") || "未命名";
  return "未保存的新草稿";
});

const isSeriesDefault = computed(
  () => props.currentDraft?.isSeriesDefault === true
);
const isGlobalDefault = computed(
  () => props.currentDraft?.isDefault === true || props.draftId === props.globalDefaultId
);

function formatTime(rec) {
  const n = rec?.updatedAt || rec?.createdAt;
  if (!n) return "";
  const d = new Date(n);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<template>
  <div class="version-rail">
    <section class="panel panel-version" :class="{ 'panel-version--collapsed': !versionPanelOpen }">
      <div class="panel-version-head">
        <h3 class="rail-title">{{ panelTitle }}</h3>
        <button
          type="button"
          class="panel-toggle"
          :aria-expanded="versionPanelOpen"
          :title="versionPanelOpen ? '收起版本与默认' : '展开版本与默认'"
          @click="toggleVersionPanel"
        >
          <span class="panel-toggle-chevron" aria-hidden="true">{{ versionPanelOpen ? "‹" : "›" }}</span>
          {{ versionPanelOpen ? "收起" : "展开" }}
        </button>
      </div>

      <div
        v-if="!versionPanelOpen"
        class="panel-version-summary"
        role="button"
        tabindex="0"
        title="点击展开版本与默认"
        @click="versionPanelOpen = true"
        @keydown.enter.prevent="versionPanelOpen = true"
      >
        <span class="panel-version-summary-title">{{ draftLabel }}</span>
        <span v-if="draftId" class="panel-version-summary-badges">
          <span v-if="isSeriesDefault" class="pill pill-series pill-xs">简历</span>
          <span v-if="isGlobalDefault" class="pill pill-global pill-xs">对话</span>
        </span>
        <span v-else class="muted small">未保存</span>
      </div>

      <div v-show="versionPanelOpen" class="panel-version-body">
      <div class="default-legend">
        <div class="legend-item">
          <span class="legend-dot legend-dot--series" />
          <div>
            <strong>本简历默认</strong>
            <p>打开该简历线时优先加载这一条副本。</p>
          </div>
        </div>
        <div class="legend-item">
          <span class="legend-dot legend-dot--global" />
          <div>
            <strong>对话默认</strong>
            <p>规划师拖入简历、对话引用时使用（全账号仅一条）。</p>
          </div>
        </div>
      </div>

      <div
        class="draft-card"
        :class="{ 'draft-card--empty': !draftId }"
        :style="{ '--draft-accent': accent }"
      >
        <div class="draft-card-label">当前编辑</div>
        <div class="draft-card-title">{{ draftLabel }}</div>
        <p v-if="currentDraft" class="draft-card-meta mono-time">
          副本 {{ formatTime(currentDraft) }}
          <span v-if="!canSaveInPlace"> · 尚未保存</span>
        </p>
        <p v-else class="draft-card-meta muted">填写后点保存，将创建新简历线</p>
        <div v-if="draftId" class="draft-badges">
          <span v-if="isSeriesDefault" class="pill pill-series">本简历默认</span>
          <span v-else class="pill pill-muted">非本简历默认</span>
          <span v-if="isGlobalDefault" class="pill pill-global">对话默认</span>
        </div>
        <div v-if="draftId && (!isSeriesDefault || !isGlobalDefault)" class="draft-quick-defaults">
          <button
            v-if="!isSeriesDefault"
            type="button"
            class="link-btn"
            @click="emit('set-default', draftId, 'series')"
          >
            设为本简历默认
          </button>
          <button
            v-if="!isGlobalDefault"
            type="button"
            class="link-btn"
            @click="emit('set-default', draftId, 'global')"
          >
            设为对话默认
          </button>
        </div>
      </div>

      <div v-if="activeSeries" class="series-versions">
        <div class="series-versions-head">
          <span>本简历副本（{{ activeSeries.versions.length }}）</span>
          <button type="button" class="link-btn" @click="emit('open-all-copies', activeSeries)">
            全部
          </button>
        </div>
        <ul class="version-mini-list">
          <li
            v-for="r in activeSeries.versions"
            :key="r.id"
            class="version-mini-row"
            :class="{ active: r.id === draftId }"
            @click="emit('load-version', r)"
          >
            <span class="mono-time">{{ formatTime(r) }}</span>
            <span class="version-mini-badges">
              <span v-if="r.isSeriesDefault" class="pill pill-series pill-xs">简历</span>
              <span v-if="r.isDefault" class="pill pill-global pill-xs">对话</span>
            </span>
          </li>
        </ul>
      </div>

      <div v-if="globalDefaultRecord && globalDefaultRecord.id !== draftId" class="global-ref muted small">
        对话默认：
        <button type="button" class="link-btn inline" @click="emit('load-version', globalDefaultRecord)">
          {{ stripTimeCopySuffix(globalDefaultRecord.displayName || "") || "查看" }}
        </button>
      </div>
      </div>
    </section>

    <section class="panel panel-save">
      <label class="field-inline">
        <span>简历名称</span>
        <input
          :value="displayName"
          placeholder="留空自动生成"
          @input="emit('update:displayName', $event.target.value)"
        />
      </label>
      <label class="checkbox-row">
        <input
          type="checkbox"
          :checked="setAsGlobalDefault"
          @change="emit('update:setAsGlobalDefault', $event.target.checked)"
        />
        <span>保存时同时设为<strong>对话默认</strong></span>
      </label>
      <p class="muted small save-hint">{{ saveHint }}</p>
      <div class="save-actions">
        <button type="button" class="btn primary block" :disabled="saving" @click="emit('save-draft')">
          {{ canSaveInPlace ? "保存当前副本" : "保存并创建首条副本" }}
        </button>
        <button
          type="button"
          class="btn ghost block"
          :disabled="saving || !canSaveInPlace"
          @click="emit('save-as-copy')"
        >
          另存为新副本
        </button>
        <div class="btn-row-secondary">
          <button type="button" class="btn ghost btn-sm" @click="emit('new-series')">新简历线</button>
          <button type="button" class="btn ghost btn-sm" @click="emit('export-json')">导出</button>
        </div>
      </div>
    </section>

    <section class="panel panel-lines">
      <h3 class="rail-title">全部简历线</h3>
      <p v-if="hasStudentContext" class="muted small lines-hint">
        学号 <code>{{ studentId }}</code>
      </p>
      <p v-else class="muted small lines-hint">未登录学号，数据仅存本机。</p>
      <p v-if="!resumeGroups.length" class="muted small">暂无，保存后出现在此。</p>
      <ul v-else class="line-list">
        <li
          v-for="g in resumeGroups"
          :key="g.seriesId"
          class="line-card"
          :class="{ active: seriesId === g.seriesId }"
          @click="emit('select-group', g)"
        >
          <div class="line-card-title">{{ g.label }}</div>
          <div class="line-card-meta">
            <span>{{ g.versions.length }} 副本</span>
            <span v-if="g.isGlobalSeries" class="pill pill-global pill-xs">对话</span>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.version-rail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.rail-title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 700;
}
.panel-version,
.panel-save,
.panel-lines {
  padding: 14px 16px;
}
.panel-version--collapsed {
  padding-bottom: 12px;
}
.panel-version-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 0;
}
.panel-version-head .rail-title {
  margin-bottom: 0;
}
.panel-version--collapsed .panel-version-head {
  margin-bottom: 0;
}
.panel-toggle {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.panel-toggle:hover {
  border-color: #c7d2fe;
  color: var(--primary-color, #4f46e5);
}
.panel-toggle-chevron {
  font-size: 0.9rem;
  line-height: 1;
}
.panel-version-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  cursor: pointer;
}
.panel-version-summary:hover {
  border-color: #c7d2fe;
  background: #f5f3ff;
}
.panel-version-summary-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: #334155;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
}
.panel-version-summary-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.panel-version-body {
  margin-top: 12px;
}
.default-legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #eef2f6;
}
.legend-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.legend-item strong {
  display: block;
  font-size: 0.78rem;
  color: #334155;
}
.legend-item p {
  margin: 2px 0 0;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.35;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-top: 5px;
  flex-shrink: 0;
}
.legend-dot--series {
  background: #6366f1;
}
.legend-dot--global {
  background: #d97706;
}
.draft-card {
  border: 1px solid color-mix(in srgb, var(--draft-accent) 35%, #e5e7eb);
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(180deg, #fff, color-mix(in srgb, var(--draft-accent) 6%, #fff));
  margin-bottom: 12px;
}
.draft-card--empty {
  border-style: dashed;
  background: #fafafa;
}
.draft-card-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin-bottom: 4px;
}
.draft-card-title {
  font-weight: 700;
  font-size: 0.92rem;
  color: #1e293b;
  margin-bottom: 4px;
}
.draft-card-meta {
  font-size: 0.75rem;
  margin: 0 0 8px;
}
.draft-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.draft-quick-defaults {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}
.pill {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.pill-xs {
  font-size: 0.62rem;
  padding: 1px 6px;
}
.pill-series {
  background: #e0e7ff;
  color: #4338ca;
}
.pill-global {
  background: #fef3c7;
  color: #b45309;
}
.pill-muted {
  background: #f1f5f9;
  color: #64748b;
}
.series-versions {
  margin-top: 4px;
}
.series-versions-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
  color: #64748b;
  margin-bottom: 6px;
}
.version-mini-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 140px;
  overflow-y: auto;
}
.version-mini-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.75rem;
  border: 1px solid transparent;
}
.version-mini-row:hover {
  background: #f1f5f9;
}
.version-mini-row.active {
  background: #eef2ff;
  border-color: #c7d2fe;
}
.version-mini-badges {
  display: flex;
  gap: 4px;
}
.global-ref {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eef2f6;
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: inherit;
  color: var(--primary-color, #4f46e5);
  cursor: pointer;
  font-weight: 600;
}
.link-btn.inline {
  font-size: 0.78rem;
}
.field-inline {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}
.field-inline span {
  font-size: 0.78rem;
  color: #64748b;
}
.field-inline input {
  padding: 9px 10px;
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  font-size: 0.88rem;
}
.checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 8px;
  cursor: pointer;
}
.checkbox-row input {
  margin-top: 3px;
}
.save-hint {
  margin: 0 0 12px;
  line-height: 1.45;
}
.save-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.btn.block {
  width: 100%;
  justify-content: center;
}
.btn-row-secondary {
  display: flex;
  gap: 8px;
}
.btn-row-secondary .btn {
  flex: 1;
}
.btn-sm {
  padding: 7px 10px;
  font-size: 0.8rem;
}
.lines-hint {
  margin: -6px 0 10px;
}
.lines-hint code {
  font-size: 0.75rem;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
}
.line-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}
.line-card {
  padding: 10px 12px;
  border: 1px solid #eceff3;
  border-radius: 10px;
  cursor: pointer;
  background: #fcfcff;
  transition: border-color 0.15s, background 0.15s;
}
.line-card:hover {
  border-color: #c7d2fe;
}
.line-card.active {
  border-color: var(--primary-color, #4f46e5);
  background: #f5f3ff;
}
.line-card-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #1e293b;
}
.line-card-meta {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 4px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.mono-time {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.muted {
  color: var(--text-muted, #64748b);
}
.small {
  font-size: 0.82rem;
}
.btn {
  padding: 10px 16px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.88rem;
  cursor: pointer;
  border: none;
}
.btn.primary {
  background: var(--primary-color, #4f46e5);
  color: #fff;
}
.btn.ghost {
  background: #fff;
  color: #334155;
  border: 1px solid #d1d5db;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
