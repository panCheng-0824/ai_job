<script setup>
/**
 * 奖惩信息弹幕跑马灯：多行横向滚动，模拟弹幕展示效果。
 */
import { computed } from "vue";

const props = defineProps({
  awards: { type: Array, default: () => [] }
});

const TONES = ["tone-a", "tone-b", "tone-c", "tone-d", "tone-e"];

/** 将奖惩记录格式化为弹幕文案 */
function formatAward(item) {
  const year = item["奖项年度"];
  const name = item["项目名称"] || item["项目类别"] || "";
  const category = item["项目类别"];
  const desc = item["项目描述"];

  const parts = [];
  if (year) parts.push(`${year}年`);
  if (name) parts.push(String(name));
  else if (category) parts.push(String(category));
  if (desc && desc !== name) {
    const short = String(desc).slice(0, 18);
    parts.push(short.length < String(desc).length ? `${short}…` : short);
  }
  return parts.join(" · ") || "奖惩记录";
}

const danmakuItems = computed(() => {
  const list = (props.awards || [])
    .map((item, index) => ({
      id: `${index}-${formatAward(item)}`,
      text: formatAward(item),
      tone: TONES[index % TONES.length]
    }))
    .filter((item) => item.text);

  if (!list.length) {
    return [{ id: "empty", text: "暂无奖惩记录，完善画像后将在此展示", tone: "tone-empty" }];
  }
  return list;
});

/** 拆成多行弹幕，行数随数据量自适应 */
const rows = computed(() => {
  const items = danmakuItems.value;
  const count = items.length;
  const rowCount = count <= 2 ? 1 : count <= 5 ? 2 : 3;
  const durations = [26, 32, 22];
  const result = [];

  for (let r = 0; r < rowCount; r += 1) {
    const rowItems = items.filter((_, i) => i % rowCount === r);
    if (!rowItems.length) continue;
    result.push({
      duration: durations[r] ?? 28,
      reverse: r % 2 === 1,
      items: rowItems
    });
  }
  return result;
});

/** 无缝循环需复制一份轨道内容 */
function trackItems(items) {
  return [...items, ...items];
}
</script>

<template>
  <div class="danmaku-wrap" aria-label="奖惩情况弹幕展示">
    <div
      v-for="(row, rowIndex) in rows"
      :key="rowIndex"
      class="danmaku-row"
    >
      <div
        class="danmaku-track"
        :class="{ 'danmaku-track--reverse': row.reverse }"
        :style="{ '--duration': `${row.duration}s` }"
      >
        <span
          v-for="(item, index) in trackItems(row.items)"
          :key="`${rowIndex}-${index}-${item.id}`"
          class="danmaku-item"
          :class="item.tone"
        >
          {{ item.text }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.danmaku-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 0;
  border-radius: 12px;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  overflow: hidden;
  min-height: 72px;
}

.danmaku-wrap::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.12), transparent 55%),
    radial-gradient(circle at 80% 70%, rgba(168, 85, 247, 0.1), transparent 50%);
  pointer-events: none;
}

.danmaku-row {
  position: relative;
  overflow: hidden;
  height: 28px;
  mask-image: linear-gradient(90deg, transparent 0%, #000 10%, #000 90%, transparent 100%);
}

.danmaku-track {
  display: flex;
  align-items: center;
  gap: 14px;
  width: max-content;
  padding: 0 8px;
  animation: danmaku-scroll var(--duration, 28s) linear infinite;
  will-change: transform;
}

.danmaku-track--reverse {
  animation-name: danmaku-scroll-reverse;
}

.danmaku-wrap:hover .danmaku-track {
  animation-play-state: paused;
}

.danmaku-item {
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(4px);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  transition: transform 0.16s ease, filter 0.16s ease, box-shadow 0.16s ease;
}

.danmaku-wrap:hover .danmaku-item:hover {
  transform: scale(1.06);
  filter: brightness(1.14);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
  z-index: 1;
}

.tone-a {
  color: #fef3c7;
  background: rgba(245, 158, 11, 0.22);
  border-color: rgba(251, 191, 36, 0.35);
}

.tone-b {
  color: #e0e7ff;
  background: rgba(99, 102, 241, 0.28);
  border-color: rgba(129, 140, 248, 0.4);
}

.tone-c {
  color: #fce7f3;
  background: rgba(236, 72, 153, 0.22);
  border-color: rgba(244, 114, 182, 0.35);
}

.tone-d {
  color: #ccfbf1;
  background: rgba(20, 184, 166, 0.22);
  border-color: rgba(45, 212, 191, 0.35);
}

.tone-e {
  color: #dbeafe;
  background: rgba(59, 130, 246, 0.24);
  border-color: rgba(96, 165, 250, 0.35);
}

.tone-empty {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.15);
  border-color: rgba(148, 163, 184, 0.25);
  font-weight: 500;
}

@keyframes danmaku-scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@keyframes danmaku-scroll-reverse {
  from {
    transform: translateX(-50%);
  }
  to {
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .danmaku-track {
    animation: none;
    flex-wrap: wrap;
    width: 100%;
    justify-content: center;
    gap: 6px;
    padding: 0 10px;
  }

  .danmaku-row {
    height: auto;
    min-height: 28px;
    mask-image: none;
  }

  .danmaku-item {
    transition: none;
  }
}
</style>
