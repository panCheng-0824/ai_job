<script setup>
/** 面试分类工作区：搜索 + 左行业树 + 右大纲列表（同面试大纲逻辑） */
import IndustryCategoryTreeList from "./IndustryCategoryTreeList.vue";
import InterviewPlanManagePanel from "./InterviewPlanManagePanel.vue";

defineProps({
  searchQuery: { type: String, default: "" },
  industryLoading: { type: Boolean, default: false },
  industryError: { type: String, default: "" },
  displayTree: { type: Array, default: () => [] },
  selectedIndustryId: { type: String, default: "" },
  searchExpandIds: { type: Array, default: () => [] },
  searchKeyword: { type: String, default: "" },
  selectedIndustry: { type: Object, default: null },
  plans: { type: Array, default: () => [] },
  plansLoading: { type: Boolean, default: false },
  plansError: { type: String, default: "" },
  guest: { type: Boolean, default: false },
  hintText: { type: String, default: "" }
});

defineEmits(["update:searchQuery", "refresh", "select-industry", "clear-search", "create", "detail", "edit", "delete"]);
</script>

<template>
  <div class="plan-workspace">
    <header v-if="hintText" class="plan-workspace-hint">
      {{ hintText }}
    </header>

    <div v-if="!industryLoading && !industryError" class="plan-search">
      <span class="plan-search-icon" aria-hidden="true">⌕</span>
      <input
        :value="searchQuery"
        type="search"
        class="plan-search-input"
        placeholder="搜索行业名称、编码…"
        autocomplete="off"
        @input="$emit('update:searchQuery', $event.target.value)"
      />
      <button v-if="searchQuery" type="button" class="plan-search-clear" @click="$emit('clear-search')">清除</button>
      <button type="button" class="plan-search-refresh" :disabled="industryLoading" @click="$emit('refresh')">刷新</button>
    </div>

    <p v-if="industryError" class="plan-error">{{ industryError }}</p>
    <p v-else-if="industryLoading" class="plan-muted">加载行业分类…</p>

    <div v-else class="plan-layout">
      <IndustryCategoryTreeList
        class="plan-layout-tree"
        readonly
        :selectable-level="2"
        :tree="displayTree"
        :selected-id="selectedIndustryId"
        :auto-expand-ids="searchExpandIds"
        :search-keyword="searchKeyword"
        @select="$emit('select-industry', $event)"
      />
      <InterviewPlanManagePanel
        class="plan-layout-panel"
        :industry="selectedIndustry"
        :plans="plans"
        :loading="plansLoading"
        :error="plansError"
        :guest="guest"
        @create="$emit('create')"
        @detail="(planId, version) => $emit('detail', planId, version)"
        @edit="(planId, version) => $emit('edit', planId, version)"
        @delete="(planId) => $emit('delete', planId)"
      />
    </div>
  </div>
</template>

<style scoped>
.plan-workspace {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.plan-workspace-hint {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #e2e8f0;
  font-size: 0.84rem;
  color: #64748b;
}

.plan-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 4px 16px rgba(91, 106, 223, 0.05);
}

.plan-search-icon {
  color: #94a3b8;
  font-size: 1rem;
  flex-shrink: 0;
}

.plan-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 0.88rem;
  color: #1e293b;
  background: transparent;
}

.plan-search-input::placeholder {
  color: #94a3b8;
}

.plan-search-clear,
.plan-search-refresh {
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.plan-search-clear {
  border: none;
  background: #f1f5f9;
}

.plan-search-clear:hover {
  background: #e2e8f0;
  color: #334155;
}

.plan-search-refresh:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}

.plan-search-refresh:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.plan-layout {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  min-height: min(720px, calc(100vh - 220px));
}

.plan-layout-tree {
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 20px);
  max-height: calc(100vh - var(--home-topbar-h, 56px) - 40px);
  overflow: auto;
  overscroll-behavior: contain;
}

.plan-layout-panel {
  min-height: 420px;
}

.plan-error {
  margin: 0;
  color: var(--danger, #dc2626);
  font-weight: 600;
  font-size: 0.88rem;
}

.plan-muted {
  margin: 0;
  color: #64748b;
  text-align: center;
  padding: 24px;
  font-size: 0.88rem;
}

@media (max-width: 900px) {
  .plan-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .plan-layout-tree {
    position: static;
    max-height: none;
  }
}
</style>
