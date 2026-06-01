<script setup>
/**
 * 面试大纲列表卡片 — 点击进入详情，底部编辑/删除不冒泡。
 */
import { computed } from "vue";
import { useRouter } from "vue-router";
import { formatDateTime } from "../../modules/interview/formatters";
import { planStatusMeta } from "../../modules/interview/planBasicMeta";
import PlanStatusPill from "./PlanStatusPill.vue";

const props = defineProps({
  item: { type: Object, required: true }
});

const emit = defineEmits(["edit", "delete"]);

const router = useRouter();

const status = computed(() => planStatusMeta(props.item?.status));

const detailTo = computed(() => ({
  path: `/interview/plans/${encodeURIComponent(props.item.plan_id)}`,
  query: { version: props.item.version }
}));

const displayTitle = computed(
  () => props.item.title || props.item.target_role || props.item.plan_id || "未命名大纲"
);

function goDetail() {
  router.push(detailTo.value);
}

function onEdit(e) {
  e.stopPropagation();
  emit("edit", props.item.plan_id, props.item.version);
}

function onDelete(e) {
  e.stopPropagation();
  emit("delete", props.item.plan_id);
}
</script>

<template>
  <li
    class="plan-card"
    role="link"
    tabindex="0"
    @click="goDetail"
    @keydown.enter="goDetail"
    @keydown.space.prevent="goDetail"
  >
    <div class="card-body">
      <header class="card-head">
        <PlanStatusPill :label="status.label" :tone="status.tone" />
        <span class="version-tag">v{{ item.version }}</span>
      </header>

      <h3 class="card-title">{{ displayTitle }}</h3>
      <p v-if="item.target_role && item.title" class="card-sub">{{ item.target_role }}</p>

      <div class="card-stats">
        <span class="stat">
          <strong>{{ item.question_count || 0 }}</strong>
          <em>题目</em>
        </span>
        <span class="stat-divider" aria-hidden="true" />
        <span class="stat stat-time">
          <em>更新</em>
          <strong>{{ formatDateTime(item.created_at) }}</strong>
        </span>
      </div>

      <span class="card-enter">查看详情 →</span>
    </div>

    <footer class="card-foot" @click.stop>
      <button type="button" class="act-btn" @click="onEdit">编辑</button>
      <button type="button" class="act-btn act-danger" @click="onDelete">删除</button>
    </footer>
  </li>
</template>

<style scoped>
.plan-card {
  list-style: none;
  display: flex;
  flex-direction: column;
  border: 1px solid #e8ecf4;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.plan-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
  transform: translateY(-2px);
}

.plan-card:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.card-body {
  flex: 1;
  padding: 14px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.version-tag {
  font-size: 0.72rem;
  font-weight: 700;
  color: #6366f1;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: ui-monospace, monospace;
}

.card-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.4;
  color: #1e293b;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.plan-card:hover .card-title {
  color: #4338ca;
}

.card-sub {
  margin: -4px 0 0;
  font-size: 0.8rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 2px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 0.78rem;
}

.stat strong {
  font-size: 0.88rem;
  font-weight: 700;
  color: #334155;
}

.stat em {
  font-style: normal;
  color: #94a3b8;
  font-size: 0.72rem;
}

.stat-time {
  min-width: 0;
  flex: 1;
}

.stat-time strong {
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-divider {
  width: 1px;
  height: 14px;
  background: #e2e8f0;
  flex-shrink: 0;
}

.card-enter {
  margin-top: auto;
  font-size: 0.72rem;
  font-weight: 600;
  color: #6366f1;
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.plan-card:hover .card-enter {
  opacity: 1;
  transform: translateX(0);
}

.card-foot {
  display: flex;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid #f1f5f9;
  background: #fafbff;
}

.act-btn {
  flex: 1;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.act-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #1e293b;
}

.act-danger {
  color: #dc2626;
  border-color: #fecaca;
}

.act-danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}
</style>
