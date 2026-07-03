<script setup>
import { computed, ref, watch } from "vue";
import {
  INTERVIEWER_PERSONAS,
  getLive2dModelLabel,
  loadRoomVoiceOutput,
  saveRoomVoiceOutput,
  selectInterviewerPersona
} from "../../config/interviewerPersonas";
import { fetchLive2dModelCatalog } from "../../config/live2dModelCatalog";
import { loadTtsVoice } from "../../config/ttsVoices";

const props = defineProps({
  voiceId: { type: String, default: () => loadTtsVoice() },
  live2dModel: { type: String, default: "Haru" },
  /** presence | live2d — 仅 live2d 时展示角色表现 */
  interviewerVisual: {
    type: String,
    default: "presence",
    validator: (v) => ["presence", "live2d"].includes(v)
  },
  collapsed: { type: Boolean, default: false }
});

const emit = defineEmits([
  "select-persona",
  "update:voiceOutput",
  "live2d-action",
  "update:collapsed"
]);

const voiceConfigExpanded = ref(true);
const voicesExpanded = ref(false);
/** 角色表现（表情/动作）默认折叠，需要时再展开 */
const characterActionsExpanded = ref(false);
const actionTab = ref("expressions");
const voiceOutputOn = ref(loadRoomVoiceOutput());

const catalog = ref(null);
const catalogLoading = ref(false);
const catalogError = ref("");

const currentPersona = computed(
  () => INTERVIEWER_PERSONAS.find((p) => p.id === props.voiceId) ?? INTERVIEWER_PERSONAS[0]
);

const motionGroups = computed(() => {
  if (!catalog.value?.motions?.length) return [];
  const map = new Map();
  for (const motion of catalog.value.motions) {
    if (!map.has(motion.group)) {
      map.set(motion.group, {
        group: motion.group,
        label: motion.groupLabel,
        items: []
      });
    }
    map.get(motion.group).items.push(motion);
  }
  return [...map.values()];
});

const actionTabs = computed(() => {
  const tabs = [];
  if (catalog.value?.hasExpressions) tabs.push({ id: "expressions", label: "表情" });
  if (catalog.value?.hasMotions) tabs.push({ id: "motions", label: "动作" });
  if (catalog.value?.hasHitAreas) tabs.push({ id: "hits", label: "交互" });
  return tabs;
});

const actionCounts = computed(() => ({
  expressions: catalog.value?.expressions?.length ?? 0,
  motions: catalog.value?.motions?.length ?? 0,
  hits: catalog.value?.hitAreas?.length ?? 0
}));

const showCharacterActions = computed(() => props.interviewerVisual === "live2d");

const panelSubtitle = computed(() =>
  showCharacterActions.value
    ? "语音播报 · 数字人 · 表情动作"
    : "语音播报 · 呼吸效果（可随时切换数字人）"
);

async function loadCatalog(modelName) {
  catalogLoading.value = true;
  catalogError.value = "";
  catalog.value = null;
  try {
    catalog.value = await fetchLive2dModelCatalog(modelName);
    const first = actionTabs.value[0]?.id;
    if (first) actionTab.value = first;
  } catch (err) {
    catalogError.value = err?.message || "角色资源加载失败";
  } finally {
    catalogLoading.value = false;
  }
}

watch(
  () => [props.live2dModel, props.interviewerVisual],
  ([model, visual]) => {
    if (visual === "live2d" && model) {
      loadCatalog(model);
    } else {
      catalog.value = null;
      catalogError.value = "";
      catalogLoading.value = false;
    }
  },
  { immediate: true }
);

function togglePanel() {
  emit("update:collapsed", !props.collapsed);
}

function toggleVoiceOutput() {
  voiceOutputOn.value = saveRoomVoiceOutput(!voiceOutputOn.value);
  emit("update:voiceOutput", voiceOutputOn.value);
}

function onSelectVoice(id) {
  const next = selectInterviewerPersona(id);
  emit("select-persona", next);
  voicesExpanded.value = false;
}

function emitLive2dAction(payload) {
  emit("live2d-action", payload);
}

function playExpression(expressionId) {
  emitLive2dAction({ type: "expression", id: expressionId });
}

function playMotion(motion) {
  emitLive2dAction({ type: "motion", group: motion.group, index: motion.index });
}

function playHitArea(areaName) {
  emitLive2dAction({ type: "hit", area: areaName });
}
</script>

<template>
  <aside class="side-panel" :class="{ 'side-panel--collapsed': collapsed }">
    <header class="side-head" :class="{ 'side-head--collapsed': collapsed }">
      <div v-if="!collapsed" class="side-head-text">
        <h2>面试官配置</h2>
        <p>{{ panelSubtitle }}</p>
      </div>
      <span v-if="!collapsed && showCharacterActions" class="model-pill">{{ live2dModel }}</span>
      <button
        type="button"
        class="panel-fold-btn"
        :title="collapsed ? '展开面试官配置' : '收起面试官配置'"
        @click="togglePanel"
      >
        <span class="panel-fold-icon" :class="{ collapsed }">‹</span>
        <span v-if="!collapsed" class="panel-fold-label">收起</span>
      </button>
    </header>

    <button
      v-if="collapsed"
      type="button"
      class="side-collapsed-rail"
      title="展开面试官配置与角色表现"
      @click="togglePanel"
    >
      <span class="side-collapsed-icon" aria-hidden="true">⚙</span>
      <span class="side-collapsed-text">面试官配置</span>
      <span v-if="showCharacterActions" class="side-collapsed-hint">角色</span>
    </button>

    <div v-show="!collapsed" class="side-scroll">
      <section class="side-block">
        <button
          type="button"
          class="side-block-toggle"
          :aria-expanded="voiceConfigExpanded"
          @click="voiceConfigExpanded = !voiceConfigExpanded"
        >
          <span class="side-block-title">语音配置</span>
          <span class="side-block-chevron" :class="{ open: voiceConfigExpanded }">▼</span>
        </button>

        <div v-show="voiceConfigExpanded" class="side-block-body">
          <div class="toggle-row">
            <div>
              <p class="toggle-label">语音播报</p>
              <p class="toggle-hint">助手回复 TTS 朗读</p>
            </div>
            <button type="button" class="toggle-switch" :class="{ on: voiceOutputOn }" @click="toggleVoiceOutput">
              {{ voiceOutputOn ? "开" : "关" }}
            </button>
          </div>

          <div
            class="persona-card"
            :class="currentPersona.gender === 'male' ? 'persona-card--male' : 'persona-card--female'"
          >
            <div class="persona-card-top">
              <span class="persona-card-title">{{ currentPersona.title }}</span>
              <span class="persona-card-accent">{{ currentPersona.accent }}</span>
            </div>
            <p class="persona-card-blurb">{{ currentPersona.blurb }}</p>
            <div class="persona-card-foot">
              <span class="persona-tag persona-tag--live2d">
                {{ showCharacterActions ? getLive2dModelLabel(live2dModel) : `数字人 · ${live2dModel}` }}
              </span>
              <span class="persona-tag persona-tag--id">{{ currentPersona.id }}</span>
            </div>
          </div>

          <button type="button" class="link-btn" @click="voicesExpanded = !voicesExpanded">
            {{ voicesExpanded ? "收起角色列表" : "更换语音角色" }}
            <span class="link-btn-chevron" :class="{ open: voicesExpanded }">▼</span>
          </button>

          <div v-show="voicesExpanded" class="persona-list-wrap">
            <p class="persona-legend">
              <span class="leg-female">女声</span>
              <span class="leg-male">男声</span>
            </p>
            <div class="persona-list">
              <button
                v-for="persona in INTERVIEWER_PERSONAS"
                :key="persona.id"
                type="button"
                class="persona-list-item"
                :class="[
                  persona.gender === 'male' ? 'persona-list-item--male' : 'persona-list-item--female',
                  { active: voiceId === persona.id }
                ]"
                @click="onSelectVoice(persona.id)"
              >
                <span class="persona-list-title">{{ persona.title }}</span>
                <span class="persona-list-sub">{{ persona.live2dLabel }}</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <section v-if="showCharacterActions" class="side-block side-block--actions">
        <button
          type="button"
          class="side-block-toggle"
          :aria-expanded="characterActionsExpanded"
          @click="characterActionsExpanded = !characterActionsExpanded"
        >
          <span class="side-block-title-wrap">
            <span class="side-block-title">角色表现</span>
            <span v-if="!characterActionsExpanded && catalog" class="side-block-badge">
              {{ (actionCounts.expressions || 0) + (actionCounts.motions || 0) }}
            </span>
          </span>
          <span class="side-block-chevron" :class="{ open: characterActionsExpanded }">▼</span>
        </button>

        <div v-show="characterActionsExpanded" class="side-block-body">
          <p v-if="catalogLoading" class="empty-hint">加载中…</p>
          <p v-else-if="catalogError" class="empty-hint empty-hint--error">{{ catalogError }}</p>
          <template v-else-if="catalog && actionTabs.length">
            <div class="action-tabs" role="tablist">
              <button
                v-for="tab in actionTabs"
                :key="tab.id"
                type="button"
                role="tab"
                class="action-tab"
                :class="{ active: actionTab === tab.id }"
                @click="actionTab = tab.id"
              >
                {{ tab.label }}
                <span class="action-tab-count">{{ actionCounts[tab.id] }}</span>
              </button>
            </div>

            <div v-show="actionTab === 'expressions'" class="action-pane">
              <div class="chip-grid chip-grid--2">
                <button
                  v-for="expr in catalog.expressions"
                  :key="expr.id"
                  type="button"
                  class="chip chip--expr"
                  @click="playExpression(expr.id)"
                >
                  <span class="chip-title">{{ expr.label }}</span>
                  <span class="chip-sub">{{ expr.id }}</span>
                </button>
              </div>
            </div>

            <div v-show="actionTab === 'motions'" class="action-pane">
              <div v-for="group in motionGroups" :key="group.group" class="motion-block">
                <p class="motion-block-label">{{ group.label }}</p>
                <div class="chip-grid">
                  <button
                    v-for="motion in group.items"
                    :key="`${motion.group}-${motion.index}`"
                    type="button"
                    class="chip chip--motion"
                    @click="playMotion(motion)"
                  >
                    <span class="chip-row">
                      <span class="chip-title">{{ motion.label }}</span>
                      <span v-if="motion.soundLabel" class="chip-sound">🔊</span>
                    </span>
                    <span class="chip-sub">{{ motion.soundLabel || group.label }}</span>
                  </button>
                </div>
              </div>
            </div>

            <div v-show="actionTab === 'hits'" class="action-pane">
              <div class="chip-grid">
                <button
                  v-for="area in catalog.hitAreas"
                  :key="area.name"
                  type="button"
                  class="chip chip--hit"
                  @click="playHitArea(area.name)"
                >
                  <span class="chip-title">{{ area.label }}</span>
                  <span class="chip-sub">{{ area.hint }}</span>
                </button>
              </div>
            </div>
          </template>
          <p v-else-if="catalog" class="empty-hint">当前角色暂无可用表现项</p>
        </div>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.side-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: linear-gradient(180deg, #fafbff 0%, #fff 28%);
  border-right: 1px solid #eef2f7;
  transition: width 0.22s ease;
}

.side-panel--collapsed {
  width: 52px;
  min-width: 52px;
  background: #fafbff;
}

.panel-fold-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 5px 8px;
  cursor: pointer;
  flex-shrink: 0;
}

.panel-fold-btn:hover {
  color: #4338ca;
  border-color: #c7d2fe;
}

.panel-fold-icon {
  display: inline-block;
  font-size: 1rem;
  line-height: 1;
  transition: transform 0.22s ease;
}

.panel-fold-icon.collapsed {
  transform: rotate(180deg);
}

.side-collapsed-rail {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 14px 0 12px;
  min-height: 0;
}

.side-collapsed-rail:hover {
  background: rgba(99, 102, 241, 0.06);
}

.side-collapsed-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 0.9rem;
  background: #eef2ff;
  color: #4338ca;
  border: 1px solid rgba(99, 102, 241, 0.18);
}

.side-collapsed-text {
  writing-mode: vertical-rl;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #6366f1;
}

.side-collapsed-hint {
  writing-mode: vertical-rl;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #94a3b8;
}

.side-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 14px 12px;
  border-bottom: 1px solid #eef2f7;
  background: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.side-head--collapsed {
  justify-content: center;
  padding: 10px 6px;
  border-bottom: none;
}

.side-head-text h2 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 800;
  color: #0f172a;
}

.side-head-text p {
  margin: 3px 0 0;
  font-size: 0.72rem;
  color: #94a3b8;
}

.model-pill {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 800;
  color: #4338ca;
  background: #eef2ff;
  border: 1px solid rgba(99, 102, 241, 0.18);
}

.side-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.side-block {
  border-radius: 14px;
  border: 1px solid #e8ecf4;
  background: #fff;
  box-shadow: 0 2px 10px rgba(91, 106, 223, 0.04);
  overflow: hidden;
}

.side-block--actions {
  flex: 1;
  min-height: 180px;
  display: flex;
  flex-direction: column;
}

.side-block--actions .side-block-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.side-block-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
}

.side-block-toggle:hover {
  background: #f1f5f9;
}

.side-block-title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.side-block-title {
  font-size: 0.8rem;
  font-weight: 800;
  color: #334155;
}

.side-block-badge {
  min-width: 18px;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 0.62rem;
  font-weight: 800;
  color: #4338ca;
  background: #eef2ff;
}

.side-block-chevron {
  font-size: 9px;
  color: #94a3b8;
  transition: transform 0.2s ease;
}

.side-block-chevron.open {
  transform: rotate(-180deg);
}

.side-block-body {
  padding: 10px 12px 12px;
  display: grid;
  gap: 10px;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.toggle-label {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  color: #334155;
}

.toggle-hint {
  margin: 2px 0 0;
  font-size: 0.68rem;
  color: #94a3b8;
}

.toggle-switch {
  border: none;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  color: #64748b;
  background: #e2e8f0;
  flex-shrink: 0;
}

.toggle-switch.on {
  color: #fff;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
}

.persona-card {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid transparent;
}

.persona-card--female {
  background: linear-gradient(145deg, #fdf2f8, #fce7f3);
  border-color: #f9a8d4;
  color: #831843;
}

.persona-card--male {
  background: linear-gradient(145deg, #eff6ff, #dbeafe);
  border-color: #93c5fd;
  color: #1e3a8a;
}

.persona-card-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.persona-card-title {
  font-size: 0.88rem;
  font-weight: 800;
}

.persona-card-accent {
  font-size: 0.68rem;
  font-weight: 700;
  opacity: 0.85;
}

.persona-card-blurb {
  margin: 6px 0 8px;
  font-size: 0.72rem;
  line-height: 1.45;
  opacity: 0.92;
}

.persona-card-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.persona-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.64rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.55);
}

.persona-tag--id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  opacity: 0.7;
}

.link-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  background: transparent;
  color: #6366f1;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}

.link-btn:hover {
  background: #eef2ff;
  border-color: #a5b4fc;
}

.link-btn-chevron {
  font-size: 9px;
  transition: transform 0.2s ease;
}

.link-btn-chevron.open {
  transform: rotate(-180deg);
}

.persona-list-wrap {
  max-height: 240px;
  overflow-y: auto;
  padding-right: 2px;
}

.persona-legend {
  display: flex;
  gap: 12px;
  margin: 0 0 8px;
  font-size: 0.68rem;
  font-weight: 700;
}

.leg-female {
  color: #be185d;
}

.leg-male {
  color: #1d4ed8;
}

.persona-list {
  display: grid;
  gap: 6px;
}

.persona-list-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.persona-list-item--female.active {
  border-color: #db2777;
  box-shadow: 0 0 0 2px rgba(219, 39, 119, 0.15);
}

.persona-list-item--male.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.persona-list-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #0f172a;
}

.persona-list-sub {
  font-size: 0.68rem;
  color: #64748b;
}

.action-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: #f1f5f9;
}

.action-tab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 7px 4px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-size: 0.72rem;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
}

.action-tab.active {
  color: #4338ca;
  background: #fff;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

.action-tab-count {
  min-width: 16px;
  padding: 0 5px;
  border-radius: 999px;
  font-size: 0.62rem;
  font-weight: 800;
  color: #6366f1;
  background: #eef2ff;
}

.action-pane {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 10px;
}

.chip-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.chip-grid--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 8px 9px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, transform 0.12s;
}

.chip:hover {
  border-color: #a5b4fc;
  transform: translateY(-1px);
}

.chip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 6px;
}

.chip-title {
  font-size: 0.74rem;
  font-weight: 700;
  color: #0f172a;
}

.chip-sub {
  font-size: 0.64rem;
  color: #64748b;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.chip-sound {
  font-size: 0.72rem;
  flex-shrink: 0;
}

.chip--expr {
  background: linear-gradient(145deg, #fff, #fdf4ff);
}

.chip--motion {
  background: linear-gradient(145deg, #fff, #eef2ff);
}

.chip--hit {
  background: linear-gradient(145deg, #fff, #ecfdf5);
}

.motion-block + .motion-block {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
}

.motion-block-label {
  margin: 0 0 6px;
  font-size: 0.68rem;
  font-weight: 800;
  color: #6366f1;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.empty-hint {
  margin: 0;
  padding: 12px 4px;
  font-size: 0.74rem;
  color: #94a3b8;
  text-align: center;
}

.empty-hint--error {
  color: #dc2626;
}
</style>
