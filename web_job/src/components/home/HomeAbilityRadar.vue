<script setup>
/**
 * 能力雷达图（纯 SVG，无第三方图表库）。
 * 支持维度 hover 高亮与入场展开动效。
 */
import { computed, ref } from "vue";

const props = defineProps({
  values: {
    type: Array,
    default: () => [82, 75, 70, 78, 68]
  },
  labels: {
    type: Array,
    default: () => ["专业能力", "沟通能力", "办公技能", "综合素养", "实践能力"]
  }
});

const activeIndex = ref(null);

const size = 220;
const cx = size / 2;
const cy = size / 2;
const maxR = 72;

const normalized = computed(() =>
  props.values.map((v) => Math.max(0.15, Math.min(1, Number(v) / 100 || 0.5)))
);

function pointAt(index, ratio) {
  const n = props.labels.length;
  const angle = (-Math.PI / 2) + (index * 2 * Math.PI) / n;
  const r = maxR * ratio;
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
}

const gridLevels = [0.25, 0.5, 0.75, 1];

const gridPolygons = computed(() =>
  gridLevels.map((level) => {
    const pts = props.labels.map((_, i) => pointAt(i, level));
    return pts.map((p) => p.join(",")).join(" ");
  })
);

const dataPolygon = computed(() => {
  const pts = normalized.value.map((v, i) => pointAt(i, v));
  return pts.map((p) => p.join(",")).join(" ");
});

const axisLines = computed(() =>
  props.labels.map((_, i) => {
    const [x, y] = pointAt(i, 1);
    return { x1: cx, y1: cy, x2: x, y2: y };
  })
);

const labelPositions = computed(() =>
  props.labels.map((label, i) => {
    const [x, y] = pointAt(i, 1.28);
    const [hx, hy] = pointAt(i, 1.05);
    return { label, x, y, hx, hy, value: props.values[i] ?? 0 };
  })
);

const vertexPoints = computed(() =>
  normalized.value.map((v, i) => {
    const [x, y] = pointAt(i, v);
    return { x, y, index: i };
  })
);

const activeTip = computed(() => {
  if (activeIndex.value === null) return null;
  const item = labelPositions.value[activeIndex.value];
  if (!item) return null;
  return {
    label: item.label,
    value: Math.round(Number(item.value) || 0),
    x: item.x,
    y: item.y
  };
});

function setActive(index) {
  activeIndex.value = index;
}

function clearActive() {
  activeIndex.value = null;
}
</script>

<template>
  <div class="radar-wrap" @mouseleave="clearActive">
    <svg :viewBox="`0 0 ${size} ${size}`" class="radar-svg" role="img" aria-label="能力雷达图">
      <polygon
        v-for="(poly, idx) in gridPolygons"
        :key="'g-' + idx"
        :points="poly"
        fill="none"
        stroke="#e5e7eb"
        stroke-width="1"
      />
      <line
        v-for="(line, idx) in axisLines"
        :key="'a-' + idx"
        :x1="line.x1"
        :y1="line.y1"
        :x2="line.x2"
        :y2="line.y2"
        class="radar-axis"
        :class="{ 'radar-axis--active': activeIndex === idx }"
        stroke="#e5e7eb"
        stroke-width="1"
      />
      <polygon
        class="radar-fill"
        :points="dataPolygon"
        fill="rgba(91, 106, 223, 0.28)"
        stroke="#5b6adf"
        stroke-width="2"
      />
      <circle
        v-for="(pt, idx) in vertexPoints"
        :key="'v-' + idx"
        :cx="pt.x"
        :cy="pt.y"
        r="3.5"
        class="radar-vertex"
        :class="{ 'radar-vertex--active': activeIndex === pt.index }"
      />
      <g
        v-for="(item, idx) in labelPositions"
        :key="'hit-' + idx"
        class="radar-hit"
        @mouseenter="setActive(idx)"
        @focusin="setActive(idx)"
        @focusout="clearActive"
      >
        <circle :cx="item.hx" :cy="item.hy" r="22" fill="transparent" class="radar-hit-area" tabindex="0" />
        <text
          :x="item.x"
          :y="item.y"
          text-anchor="middle"
          dominant-baseline="middle"
          class="radar-label"
          :class="{ 'radar-label--active': activeIndex === idx }"
        >
          {{ item.label }}
        </text>
      </g>
    </svg>

    <Transition name="radar-tip-fade">
      <div
        v-if="activeTip"
        class="radar-tip"
        :style="{ left: `${(activeTip.x / size) * 100}%`, top: `${(activeTip.y / size) * 100}%` }"
        role="tooltip"
      >
        <span class="radar-tip-label">{{ activeTip.label }}</span>
        <strong class="radar-tip-value">{{ activeTip.value }}</strong>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.radar-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 4px 0 0;
}

.radar-svg {
  width: 100%;
  max-width: 240px;
  height: auto;
  overflow: visible;
}

.radar-fill {
  transform-box: fill-box;
  transform-origin: center;
  animation: radar-expand 0.7s cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

.radar-axis {
  transition: stroke 0.18s ease, stroke-width 0.18s ease;
}

.radar-axis--active {
  stroke: #818cf8;
  stroke-width: 1.6;
}

.radar-vertex {
  fill: #5b6adf;
  opacity: 0.55;
  transition: opacity 0.18s ease, r 0.18s ease;
}

.radar-vertex--active {
  opacity: 1;
}

.radar-hit-area {
  cursor: default;
  outline: none;
}

.radar-hit-area:focus-visible {
  stroke: #818cf8;
  stroke-width: 1.5;
  fill: rgba(129, 140, 248, 0.08);
}

.radar-label {
  font-size: 10px;
  fill: #64748b;
  font-weight: 500;
  pointer-events: none;
  transition: fill 0.18s ease, font-weight 0.18s ease;
}

.radar-label--active {
  fill: #4338ca;
  font-weight: 700;
}

.radar-tip {
  position: absolute;
  transform: translate(-50%, calc(-100% - 10px));
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #1e293b;
  color: #f8fafc;
  font-size: 0.68rem;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.2);
}

.radar-tip-label {
  color: #cbd5e1;
}

.radar-tip-value {
  font-size: 0.82rem;
  font-weight: 800;
  color: #fff;
}

.radar-tip-fade-enter-active,
.radar-tip-fade-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.radar-tip-fade-enter-from,
.radar-tip-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, calc(-100% - 6px)) scale(0.94);
}

@keyframes radar-expand {
  from {
    opacity: 0;
    transform: scale(0.35);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .radar-fill {
    animation: none;
  }

  .radar-axis,
  .radar-vertex,
  .radar-label,
  .radar-tip-fade-enter-active,
  .radar-tip-fade-leave-active {
    transition: none;
  }
}
</style>
