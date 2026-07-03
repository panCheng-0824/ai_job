<script setup>
/** 面试分类工作区：工具栏 + 搜索 + 左树右详情 */
import IndustryCategoryDetailPanel from "./IndustryCategoryDetailPanel.vue";
import IndustryCategoryTreeList from "./IndustryCategoryTreeList.vue";

defineProps({
  searchQuery: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  loadError: { type: String, default: "" },
  displayTree: { type: Array, default: () => [] },
  selectedId: { type: String, default: "" },
  searchExpandIds: { type: Array, default: () => [] },
  searchKeyword: { type: String, default: "" },
  detail: { type: Object, default: null },
  detailLoading: { type: Boolean, default: false },
  statsText: { type: String, default: "" }
});

defineEmits([
  "update:searchQuery",
  "refresh",
  "select",
  "edit",
  "delete",
  "add-child",
  "create-l1",
  "clear-search"
]);
</script>

<template>
  <div class="industry-body">
    <header class="industry-toolbar">
      <div class="industry-toolbar-left">
        <button type="button" class="industry-btn industry-btn--primary" @click="$emit('create-l1')">
          + 新增一级
        </button>
        <button type="button" class="industry-btn industry-btn--ghost" :disabled="loading" @click="$emit('refresh')">
          刷新
        </button>
      </div>
      <span class="industry-stats">{{ statsText }}</span>
    </header>

    <div v-if="!loading && !loadError" class="industry-search">
      <span class="industry-search-icon" aria-hidden="true">⌕</span>
      <input
        :value="searchQuery"
        type="search"
        class="industry-search-input"
        placeholder="搜索名称、编码、ID、关键词、描述…"
        autocomplete="off"
        @input="$emit('update:searchQuery', $event.target.value)"
      />
      <button v-if="searchQuery" type="button" class="industry-search-clear" @click="$emit('clear-search')">
        清除
      </button>
    </div>

    <p v-if="loadError" class="industry-error">{{ loadError }}</p>
    <p v-else-if="loading" class="industry-muted">加载中…</p>

    <div v-else class="industry-layout">
      <IndustryCategoryTreeList
        class="industry-layout-tree"
        :tree="displayTree"
        :selected-id="selectedId"
        :auto-expand-ids="searchExpandIds"
        :search-keyword="searchKeyword"
        @select="$emit('select', $event)"
        @edit="$emit('edit', $event)"
        @delete="$emit('delete', $event)"
        @add-child="$emit('add-child', $event)"
      />
      <IndustryCategoryDetailPanel
        class="industry-layout-detail"
        :detail="detail"
        :loading="detailLoading"
        @edit="$emit('edit', $event)"
        @delete="$emit('delete', $event)"
        @add-child="$emit('add-child', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.industry-body {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.industry-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 4px 16px rgba(91, 106, 223, 0.05);
}

.industry-toolbar-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.industry-stats {
  font-size: 0.78rem;
  color: #64748b;
  white-space: nowrap;
}

.industry-btn {
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.industry-btn--primary {
  border: 1px solid transparent;
  background: linear-gradient(135deg, #6366f1 0%, #5b6adf 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.22);
}

.industry-btn--primary:hover {
  filter: brightness(1.03);
}

.industry-btn--ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
}

.industry-btn--ghost:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}

.industry-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.industry-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.92);
}

.industry-search-icon {
  color: #94a3b8;
  font-size: 1rem;
  flex-shrink: 0;
}

.industry-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 0.88rem;
  color: #1e293b;
  background: transparent;
}

.industry-search-input::placeholder {
  color: #94a3b8;
}

.industry-search-clear {
  flex-shrink: 0;
  border: none;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.industry-search-clear:hover {
  background: #e2e8f0;
  color: #334155;
}

.industry-layout {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  min-height: min(720px, calc(100vh - 220px));
}

.industry-layout-tree {
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 20px);
  max-height: calc(100vh - var(--home-topbar-h, 56px) - 40px);
  overflow: auto;
  overscroll-behavior: contain;
}

.industry-layout-detail {
  min-height: 420px;
}

.industry-error {
  margin: 0;
  color: var(--danger, #dc2626);
  font-weight: 600;
  font-size: 0.88rem;
}

.industry-muted {
  margin: 0;
  color: #64748b;
  text-align: center;
  padding: 24px;
  font-size: 0.88rem;
}

@media (max-width: 900px) {
  .industry-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .industry-layout-tree {
    position: static;
    max-height: none;
  }
}
</style>
