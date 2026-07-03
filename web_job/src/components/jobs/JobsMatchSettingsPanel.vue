<script setup>
/**
 * 岗位中心 · 智能匹配 Tab 下的匹配设置。
 */
import { computed, ref } from "vue";
import { apiPost } from "../../api/client";
import {
  SCORE_DIMENSION_DEFS,
  clampDimensionScore,
  cloneDefaultScoreDimensions,
  sumScoreDimensions
} from "../../constants/jobScoreRubric";
import { MATCH_PRESETS } from "../../config/matchPresets";

defineProps({
  loading: { type: Boolean, default: false },
  hint: {
    type: String,
    default: "拖动滑块调整参数后，点击「重新匹配」刷新结果；左侧筛选可用于二次过滤。"
  }
});

const emit = defineEmits(["run", "cache-cleared"]);

const query = defineModel("query", { type: String, default: "" });
const useStudentProfile = defineModel("useStudentProfile", { type: Boolean, default: true });
const useSemanticCache = defineModel("useSemanticCache", { type: Boolean, default: true });
const scoreBaseline = defineModel("scoreBaseline", { type: Number, default: 85 });
const minRecommendScore = defineModel("minRecommendScore", { type: Number, default: 85 });
const topNJobs = defineModel("topNJobs", { type: Number, default: 9 });
const scoreDimensions = defineModel("scoreDimensions", {
  type: Object,
  default: () => cloneDefaultScoreDimensions()
});

const scoreDimensionDefs = SCORE_DIMENSION_DEFS;
const TOP_N_MAX = 20;

const scoreDimensionsTotal = computed(() => sumScoreDimensions(scoreDimensions.value));
const scoreDimensionsValid = computed(() => scoreDimensionsTotal.value === 100);

const activePreset = ref(null);
const cacheClearing = ref(false);
const cacheClearMessage = ref("");
const cacheClearOk = ref(false);

const dimensionColors = {
  major: "#6366f1",
  skill: "#8b5cf6",
  threshold: "#0ea5e9",
  intent: "#14b8a6",
  quality: "#f59e0b"
};

const dimensionSegments = computed(() => {
  const total = scoreDimensionsTotal.value || 1;
  return scoreDimensionDefs.map((dim) => ({
    key: dim.key,
    label: dim.label,
    value: Number(scoreDimensions.value[dim.key]) || 0,
    widthPct: ((Number(scoreDimensions.value[dim.key]) || 0) / total) * 100,
    color: dimensionColors[dim.key] || "#94a3b8"
  }));
});

function applyPreset(preset) {
  activePreset.value = preset.key;
  scoreDimensions.value = { ...preset.weights };
}

function clampScore(value, fallback = 85) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

function clampTopN(value, fallback = 9) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.min(TOP_N_MAX, n));
}

function pct(min, max, value) {
  const span = max - min;
  if (span <= 0) return "0%";
  return `${((clampBetween(value, min, max) - min) / span) * 100}%`;
}

function clampBetween(value, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function onScoreInput(key, raw) {
  const dim = scoreDimensionDefs.find((d) => d.key === key);
  const fallback = dim ? cloneDefaultScoreDimensions()[key] : 0;
  scoreDimensions.value = {
    ...scoreDimensions.value,
    [key]: clampDimensionScore(raw, fallback)
  };
}

function onScoreBaselineInput(raw) {
  scoreBaseline.value = clampScore(raw);
}

function onMinRecommendScoreInput(raw) {
  minRecommendScore.value = clampScore(raw);
}

function onTopNInput(raw) {
  topNJobs.value = clampTopN(raw);
}

async function clearSemanticCache() {
  if (cacheClearing.value) return;
  if (!window.confirm("确定清除岗位推荐语义缓存？下次匹配将重新检索并分析。")) return;
  cacheClearing.value = true;
  cacheClearMessage.value = "";
  cacheClearOk.value = false;
  try {
    const data = await apiPost("/api/skills/job-info-sem-cache/clear", {});
    const deleted = Number(data?.deleted_keys ?? 0);
    cacheClearOk.value = Boolean(data?.cleared);
    cacheClearMessage.value = data?.message
      ? `${data.message}${deleted ? `（${deleted} 个键）` : ""}`
      : deleted
        ? `已清除 ${deleted} 个缓存键`
        : "语义缓存已清空";
    emit("cache-cleared");
  } catch (e) {
    cacheClearMessage.value = e.message || "清除语义缓存失败";
    cacheClearOk.value = false;
  } finally {
    cacheClearing.value = false;
  }
}
</script>

<template>
  <div class="match-settings">
    <div class="line">
      <input
        v-model="query"
        placeholder="例如：想找杭州前端、双休、成长空间好的岗位"
        @keydown.enter.prevent="emit('run')"
      />
      <button type="button" class="match-btn" :disabled="loading" @click="emit('run')">
        {{ loading ? "匹配中…" : "重新匹配" }}
      </button>
    </div>

    <details class="match-advanced-wrap">
      <summary>更多匹配设置</summary>
      <div class="match-advanced-body">
        <div class="preset-bar">
          <button
            v-for="p in MATCH_PRESETS"
            :key="p.key"
            type="button"
            class="preset-chip"
            :class="{ active: activePreset === p.key }"
            :title="p.desc"
            @click="applyPreset(p)"
          >
            <span class="preset-chip-icon">{{ p.icon }}</span>
            <span class="preset-chip-label">{{ p.label }}</span>
          </button>
        </div>

        <div class="toggle-row">
          <button
            type="button"
            class="toggle-pill"
            :class="{ 'toggle-pill--on': useStudentProfile }"
            @click="useStudentProfile = !useStudentProfile"
          >
            关联本人画像
          </button>
          <div class="semantic-cache-group">
            <button
              type="button"
              class="toggle-pill"
              :class="{ 'toggle-pill--on': useSemanticCache }"
              @click="useSemanticCache = !useSemanticCache"
            >
              语义缓存
            </button>
            <button
              type="button"
              class="clear-cache-btn"
              :disabled="cacheClearing"
              title="清除 Redis 中的岗位推荐语义/精确缓存"
              @click="clearSemanticCache"
            >
              {{ cacheClearing ? "清除中…" : "清除缓存" }}
            </button>
          </div>
        </div>
        <p
          v-if="cacheClearMessage"
          class="cache-clear-msg"
          :class="{ 'cache-clear-msg--ok': cacheClearOk, 'cache-clear-msg--err': !cacheClearOk }"
        >
          {{ cacheClearMessage }}
        </p>

        <section class="slider-group" aria-label="推荐阈值与数量">
          <div class="slider-field">
            <div class="slider-head">
              <span class="slider-label">评分基准</span>
              <span class="slider-value">{{ scoreBaseline }} 分</span>
            </div>
            <div class="slider-track-wrap" :style="{ '--fill': pct(0, 100, scoreBaseline) }">
              <input
                :value="scoreBaseline"
                type="range"
                min="0"
                max="100"
                step="1"
                class="match-range"
                @input="onScoreBaselineInput($event.target.value)"
              />
            </div>
            <p class="slider-hint">良好匹配的参考分数线</p>
          </div>

          <div class="slider-field">
            <div class="slider-head">
              <span class="slider-label">最低推荐分</span>
              <span class="slider-value">{{ minRecommendScore }} 分</span>
            </div>
            <div class="slider-track-wrap" :style="{ '--fill': pct(0, 100, minRecommendScore) }">
              <input
                :value="minRecommendScore"
                type="range"
                min="0"
                max="100"
                step="1"
                class="match-range"
                @input="onMinRecommendScoreInput($event.target.value)"
              />
            </div>
            <p class="slider-hint">低于此分数的岗位不会进入推荐列表</p>
          </div>

          <div class="slider-field slider-field--count">
            <div class="slider-head">
              <span class="slider-label">推荐岗位数量</span>
              <span class="slider-value slider-value--accent">{{ topNJobs }} / {{ TOP_N_MAX }} 条</span>
            </div>
            <div class="slider-track-wrap" :style="{ '--fill': pct(1, TOP_N_MAX, topNJobs) }">
              <input
                :value="topNJobs"
                type="range"
                min="1"
                :max="TOP_N_MAX"
                step="1"
                class="match-range"
                @input="onTopNInput($event.target.value)"
              />
            </div>
            <div class="count-ticks" aria-hidden="true">
              <span v-for="n in TOP_N_MAX" :key="n" class="count-tick" :class="{ active: n <= topNJobs }" />
            </div>
          </div>
        </section>

        <section class="dim-section">
          <div class="dim-section-head">
            <p class="dim-section-title">五维评分权重</p>
            <span class="dim-total" :class="{ 'dim-total--warn': !scoreDimensionsValid }">
              合计 {{ scoreDimensionsTotal }} / 100
            </span>
          </div>

          <div class="dim-stack" role="img" :aria-label="`权重分布合计 ${scoreDimensionsTotal} 分`">
            <div
              v-for="seg in dimensionSegments"
              :key="seg.key"
              class="dim-stack-seg"
              :style="{ width: `${seg.widthPct}%`, background: seg.color }"
              :title="`${seg.label} ${seg.value}`"
            />
          </div>
          <div class="dim-legend">
            <span v-for="seg in dimensionSegments" :key="`leg-${seg.key}`" class="dim-legend-item">
              <i class="dim-dot" :style="{ background: seg.color }" />
              {{ seg.label }}
            </span>
          </div>

          <div class="dim-sliders">
            <div v-for="dim in scoreDimensionDefs" :key="dim.key" class="slider-field slider-field--dim">
              <div class="slider-head">
                <span class="slider-label">{{ dim.label }}</span>
                <span class="slider-value">{{ scoreDimensions[dim.key] ?? 0 }}</span>
              </div>
              <div
                class="slider-track-wrap"
                :style="{
                  '--fill': pct(0, 100, scoreDimensions[dim.key]),
                  '--accent': dimensionColors[dim.key]
                }"
              >
                <input
                  :value="scoreDimensions[dim.key]"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  class="match-range match-range--dim"
                  @input="onScoreInput(dim.key, $event.target.value)"
                />
              </div>
              <p class="slider-hint">{{ dim.desc }}</p>
            </div>
          </div>
        </section>

        <p class="match-hint">{{ hint }}</p>
      </div>
    </details>
  </div>
</template>

<style scoped>
.match-settings {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.line {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}
.line input {
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.86rem;
}
.match-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  background: var(--home-primary, #5b6adf);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.match-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.match-advanced-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #fafbff, #fff);
  padding: 8px 12px;
}
.match-advanced-wrap > summary {
  cursor: pointer;
  color: #475569;
  font-size: 0.84rem;
  font-weight: 700;
  list-style: none;
  user-select: none;
}
.match-advanced-wrap > summary::-webkit-details-marker {
  display: none;
}
.match-advanced-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}
.preset-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.preset-chip:hover {
  border-color: #c7d2fe;
  background: #f8faff;
}
.preset-chip.active {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}
.preset-chip-icon { font-size: 1rem; }
.preset-chip-label { white-space: nowrap; }
.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.toggle-pill {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 6px 14px;
  background: #fff;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.toggle-pill:hover {
  border-color: #c7d2fe;
}
.toggle-pill--on {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
}
.semantic-cache-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.clear-cache-btn {
  border: 1px solid #fecaca;
  border-radius: 999px;
  padding: 6px 12px;
  background: #fff;
  color: #b91c1c;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.clear-cache-btn:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #f87171;
}
.clear-cache-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.cache-clear-msg {
  margin: -6px 0 0;
  font-size: 0.72rem;
  line-height: 1.45;
}
.cache-clear-msg--ok {
  color: #047857;
}
.cache-clear-msg--err {
  color: #b91c1c;
}
.slider-group {
  display: grid;
  gap: 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #eceff3;
  background: #fcfcff;
}
.slider-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.slider-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.slider-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #334155;
}
.slider-value {
  font-size: 0.8rem;
  font-weight: 800;
  color: #4338ca;
  font-variant-numeric: tabular-nums;
}
.slider-value--accent {
  color: #5b6adf;
}
.slider-hint {
  margin: 0;
  font-size: 0.72rem;
  color: #94a3b8;
  line-height: 1.4;
}
.slider-track-wrap {
  --fill: 0%;
  --accent: #6366f1;
  position: relative;
  height: 28px;
  display: flex;
  align-items: center;
}
.match-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  outline: none;
  cursor: pointer;
  background: linear-gradient(
    to right,
    var(--accent, #6366f1) 0%,
    var(--accent, #6366f1) var(--fill),
    #e2e8f0 var(--fill),
    #e2e8f0 100%
  );
}
.match-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #fff;
  background: var(--accent, #6366f1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
  cursor: grab;
  transition: transform 0.12s ease;
}
.match-range:active::-webkit-slider-thumb {
  cursor: grabbing;
  transform: scale(1.08);
}
.match-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #fff;
  background: var(--accent, #6366f1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
  cursor: grab;
}
.match-range::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  background: transparent;
}
.count-ticks {
  display: flex;
  gap: 2px;
  margin-top: 2px;
}
.count-tick {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: #e2e8f0;
  transition: background 0.15s ease;
}
.count-tick.active {
  background: #a5b4fc;
}
.dim-section {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}
.dim-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.dim-section-title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #374151;
}
.dim-total {
  font-size: 0.76rem;
  font-weight: 700;
  color: #4338ca;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
}
.dim-total--warn {
  color: #b45309;
  background: #fffbeb;
}
.dim-stack {
  display: flex;
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #f1f5f9;
  margin-bottom: 8px;
}
.dim-stack-seg {
  min-width: 0;
  transition: width 0.2s ease;
}
.dim-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-bottom: 12px;
}
.dim-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.7rem;
  color: #64748b;
}
.dim-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dim-sliders {
  display: grid;
  gap: 12px;
}
.slider-field--dim .slider-value {
  color: var(--accent, #4338ca);
}
.match-hint {
  margin: 0;
  font-size: 0.76rem;
  color: #94a3b8;
  line-height: 1.5;
}
@media (max-width: 900px) {
  .preset-bar { gap: 6px; }
  .preset-chip {
    font-size: 0.76rem;
    padding: 6px 10px;
  }
}
</style>
