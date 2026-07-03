<script setup>
/**
 * 匹配历史时间线：分页展示，滚动触底加载更多（每页 8 条）。
 */
import { computed, ref } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] },
  activeId: { type: [Number, String], default: null },
  loading: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  hasMore: { type: Boolean, default: false },
  /** 嵌入侧栏时占满高度，列表区域内部滚动 */
  fillHeight: { type: Boolean, default: false }
});

const emit = defineEmits(["select", "load-more"]);

const hoverId = ref(null);
const scrollRef = ref(null);

const hasItems = computed(() => (props.items || []).length > 0);
const countLabel = computed(() => {
  const total = props.total || props.items.length;
  if (!total) return "";
  if (props.hasMore || total > props.items.length) {
    return `已加载 ${props.items.length} / ${total}`;
  }
  return `共 ${total} 次`;
});

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatFullTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function summaryText(item) {
  const q = queryText(item);
  if (!q) return "未命名匹配";
  return q.length > 36 ? `${q.slice(0, 36)}…` : q;
}

function queryText(item) {
  return String(item?.query || item?.query_text || "").trim();
}

function isActive(id) {
  return props.activeId != null && String(props.activeId) === String(id);
}

function isHovered(id) {
  return hoverId.value != null && String(hoverId.value) === String(id);
}

function onItemEnter(id) {
  hoverId.value = id;
}

function onItemLeave() {
  hoverId.value = null;
}

/** 滚动接近底部时触发加载下一页 */
function onScroll() {
  const el = scrollRef.value;
  if (!el || props.loading || props.loadingMore || !props.hasMore) return;
  const remain = el.scrollHeight - el.scrollTop - el.clientHeight;
  if (remain <= 48) {
    emit("load-more");
  }
}
</script>

<template>
  <section class="history-timeline card-panel" :class="{ 'history-timeline--fill': fillHeight }">
    <header class="timeline-head">
      <h2>匹配记录</h2>
      <span v-if="hasItems || total" class="count-badge">{{ countLabel }}</span>
    </header>

    <div v-if="loading" class="timeline-loading">加载记录中…</div>

    <div v-else-if="!hasItems" class="timeline-empty">
      <p>暂无匹配记录</p>
      <p class="timeline-empty-hint">发起第一次匹配后，结果会保存在这里</p>
    </div>

    <div v-else ref="scrollRef" class="timeline-scroll" @scroll.passive="onScroll">
      <ol class="timeline-list" aria-label="匹配历史时间线">
        <li
          v-for="(item, index) in items"
          :key="item.id"
          class="timeline-item"
          :class="{
            'timeline-item--active': isActive(item.id),
            'timeline-item--hover': isHovered(item.id)
          }"
          @mouseenter="onItemEnter(item.id)"
          @mouseleave="onItemLeave"
        >
          <button
            type="button"
            class="timeline-btn"
            :aria-current="isActive(item.id) ? 'true' : undefined"
            :aria-describedby="isHovered(item.id) ? `timeline-popover-${item.id}` : undefined"
            @click="emit('select', item)"
          >
            <span class="timeline-dot" aria-hidden="true" />
            <span class="timeline-body">
              <span class="timeline-meta">
                <time>{{ formatTime(item.created_at) }}</time>
                <span v-if="index === 0" class="latest-tag">最新</span>
              </span>
              <span class="timeline-title">{{ summaryText(item) }}</span>
              <span class="timeline-sub">{{ item.job_count || 0 }} 个岗位</span>
            </span>
          </button>

          <Transition name="popover-fade">
            <div
              v-if="isHovered(item.id)"
              :id="`timeline-popover-${item.id}`"
              class="timeline-popover"
              role="tooltip"
            >
              <div class="popover-arrow" aria-hidden="true" />
              <p class="popover-label">推荐时间</p>
              <p class="popover-time">{{ formatFullTime(item.created_at) }}</p>
              <p class="popover-label">匹配问题</p>
              <p class="popover-query">{{ queryText(item) || "—" }}</p>
              <p class="popover-foot">{{ item.job_count || 0 }} 个推荐岗位</p>
            </div>
          </Transition>
        </li>
      </ol>

      <div v-if="loadingMore" class="timeline-more">加载更多…</div>
      <p v-else-if="!hasMore && items.length" class="timeline-end">已加载全部记录</p>
      <button
        v-else-if="hasMore"
        type="button"
        class="timeline-more-btn"
        @click="emit('load-more')"
      >
        加载更多
      </button>
    </div>
  </section>
</template>

<style scoped>
.history-timeline {
  margin-top: 12px;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px 14px 14px;
  overflow: visible;
}
.history-timeline--fill {
  margin-top: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
  overflow: hidden;
}
.history-timeline--fill .timeline-head {
  flex-shrink: 0;
  margin-bottom: 10px;
}
.history-timeline--fill .timeline-loading,
.history-timeline--fill .timeline-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.timeline-head h2 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
}
.count-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.68rem;
  font-weight: 600;
  white-space: nowrap;
}
.timeline-loading,
.timeline-empty {
  padding: 16px 8px;
  text-align: center;
  color: #94a3b8;
  font-size: 0.8rem;
}
.timeline-empty p {
  margin: 0;
}
.timeline-empty-hint {
  margin-top: 6px !important;
  font-size: 0.72rem;
  line-height: 1.5;
}
.timeline-scroll {
  max-height: min(60vh, 520px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 2px;
}
.history-timeline--fill .timeline-scroll {
  flex: 1;
  min-height: 0;
  max-height: none;
}
.timeline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  overflow: visible;
}
.timeline-list::before {
  content: "";
  position: absolute;
  left: 9px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: linear-gradient(180deg, #c7d2fe, #e2e8f0);
  border-radius: 1px;
}
.timeline-item {
  position: relative;
  overflow: visible;
}
.timeline-btn {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 6px 8px 0;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  border-radius: 10px;
  transition: background 0.15s;
}
.timeline-btn:hover,
.timeline-item--hover .timeline-btn {
  background: #f8faff;
}
.timeline-item--active .timeline-btn {
  background: #eef2ff;
}
.timeline-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  margin-top: 4px;
  margin-left: 5px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #a5b4fc;
  position: relative;
  z-index: 1;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}
.timeline-item--hover .timeline-dot,
.timeline-item--active .timeline-dot {
  background: #6366f1;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}
.timeline-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.timeline-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.68rem;
  color: #94a3b8;
}
.latest-tag {
  padding: 1px 6px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #059669;
  font-weight: 700;
  font-size: 0.62rem;
}
.timeline-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: #334155;
  line-height: 1.4;
}
.timeline-sub {
  font-size: 0.68rem;
  color: #64748b;
}
.timeline-more,
.timeline-end {
  margin: 8px 0 0;
  padding: 8px 4px 4px;
  text-align: center;
  font-size: 0.72rem;
  color: #94a3b8;
}
.timeline-more-btn {
  display: block;
  width: 100%;
  margin-top: 8px;
  padding: 8px 10px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}
.timeline-more-btn:hover {
  border-color: #a5b4fc;
  color: #4338ca;
  background: #eef2ff;
}

.timeline-popover {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%);
  z-index: 120;
  width: min(280px, 72vw);
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e0e7ff;
  background: #fff;
  box-shadow:
    0 12px 32px rgba(15, 23, 42, 0.12),
    0 2px 8px rgba(99, 102, 241, 0.08);
  pointer-events: none;
}
.popover-arrow {
  position: absolute;
  left: -6px;
  top: 50%;
  width: 10px;
  height: 10px;
  background: #fff;
  border-left: 1px solid #e0e7ff;
  border-bottom: 1px solid #e0e7ff;
  transform: translateY(-50%) rotate(45deg);
}
.popover-label {
  margin: 0 0 4px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #6366f1;
  letter-spacing: 0.04em;
}
.popover-time {
  margin: 0 0 10px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}
.popover-query {
  margin: 0;
  font-size: 0.78rem;
  color: #475569;
  line-height: 1.55;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.popover-foot {
  margin: 10px 0 0;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
  font-size: 0.68rem;
  color: #94a3b8;
}

.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(-4px);
}

@media (max-width: 1100px) {
  .timeline-popover {
    left: 0;
    right: 0;
    top: calc(100% + 4px);
    transform: none;
    width: auto;
  }
  .popover-arrow {
    left: 14px;
    top: -6px;
    transform: rotate(135deg);
  }
  .popover-fade-enter-from,
  .popover-fade-leave-to {
    transform: translateY(-4px);
  }
}
</style>
