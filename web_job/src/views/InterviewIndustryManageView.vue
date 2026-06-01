<script setup>
/**
 * 行业分类维护页：左侧可折叠树 + 右侧详情 + 弹窗表单 CRUD。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import IndustryCategoryDetailPanel from "../components/interview/IndustryCategoryDetailPanel.vue";
import IndustryCategoryFormModal from "../components/interview/IndustryCategoryFormModal.vue";
import IndustryCategoryTreeList from "../components/interview/IndustryCategoryTreeList.vue";
import { useIndustryCategoryManage } from "../composables/useIndustryCategoryManage";
import { countIndustryCategoryTree, filterIndustryCategoryTree } from "../modules/interview/industryTreeFilter";

const manage = useIndustryCategoryManage();
const route = useRoute();
const selectedId = ref("");
const searchQuery = ref("");

const isEmbed = computed(() => route.query._embed === "1");

const {
  tree,
  loadError,
  loading,
  detail,
  detailLoading,
  formVisible,
  formMode,
  form,
  formError,
  saving,
  loadTree,
  openDetail,
  openCreate,
  openEdit,
  closeForm,
  submitForm,
  removeCategory
} = manage;

function updateForm(v) {
  form.value = v;
}

const level1Options = computed(() =>
  (tree.value || []).map((x) => ({ category_id: x.category_id, category_name: x.category_name }))
);

const stats = computed(() => countIndustryCategoryTree(tree.value));

const searchResult = computed(() => filterIndustryCategoryTree(tree.value, searchQuery.value));

const displayTree = computed(() => searchResult.value.items);

const searchExpandIds = computed(() => searchResult.value.expandIds);

const isSearching = computed(() => searchQuery.value.trim().length > 0);

function clearSearch() {
  searchQuery.value = "";
}

async function onSelect(id) {
  selectedId.value = id;
  await openDetail(id);
}

async function onSubmitForm() {
  const id = await submitForm();
  if (id) selectedId.value = id;
}

function onAddChild(parentId) {
  openCreate(2, parentId);
}

async function onDelete(id) {
  const deleted = await removeCategory(id);
  if (deleted && selectedId.value === id) selectedId.value = "";
}

onMounted(loadTree);
</script>

<template>
  <div class="industry-page" :class="{ 'industry-page--embed': isEmbed }">
    <section class="hero">
      <h1>行业分类</h1>
      <p>维护一级 / 二级行业字典，供大纲分类与意图识别使用。</p>
    </section>

    <div class="container">
      <header class="toolbar">
        <div class="toolbar-left">
          <button type="button" class="btn primary" @click="openCreate(1)">+ 新增一级</button>
          <button type="button" class="btn ghost" :disabled="loading" @click="loadTree">刷新</button>
        </div>
        <p v-if="!loading && tree.length" class="stats">
          <template v-if="isSearching">
            匹配 {{ searchResult.matchCount }} 项
          </template>
          <template v-else>
            一级 {{ stats.l1 }} · 二级 {{ stats.l2 }}
          </template>
        </p>
      </header>

      <div v-if="!loading && !loadError" class="search-bar">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          v-model="searchQuery"
          type="search"
          class="search-input"
          placeholder="搜索名称、编码、ID、关键词、描述…"
          autocomplete="off"
        />
        <button v-if="searchQuery" type="button" class="search-clear" @click="clearSearch">清除</button>
      </div>

      <p v-if="loadError" class="error">{{ loadError }}</p>
      <p v-else-if="loading" class="muted">加载中…</p>

      <div v-else class="layout">
        <IndustryCategoryTreeList
          class="layout-tree"
          :tree="displayTree"
          :selected-id="selectedId"
          :auto-expand-ids="searchExpandIds"
          :search-keyword="searchQuery.trim()"
          @select="onSelect"
          @edit="openEdit"
          @delete="onDelete"
          @add-child="onAddChild"
        />
        <IndustryCategoryDetailPanel
          class="layout-detail"
          :detail="detail"
          :loading="detailLoading"
          @edit="openEdit"
          @delete="onDelete"
          @add-child="onAddChild"
        />
      </div>
    </div>

    <IndustryCategoryFormModal
      :visible="formVisible"
      :mode="formMode"
      :form="form"
      :level1-options="level1Options"
      :error="formError"
      :saving="saving"
      @close="closeForm"
      @submit="onSubmitForm"
      @update:form="updateForm"
    />
  </div>
</template>

<style scoped>
.industry-page {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 220px);
}

.industry-page--embed .hero {
  padding: 12px 16px 8px;
}

.industry-page--embed .hero h1 {
  font-size: 1.15rem;
}

.hero {
  flex-shrink: 0;
  padding: 88px 20px 16px;
  text-align: center;
}

.hero h1 {
  margin: 0 0 6px;
  font-size: 1.45rem;
}

.hero p {
  margin: 0;
  color: var(--text-muted, #6b7280);
  font-size: 0.92rem;
}

.container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 0 18px 16px;
}

.industry-page:not(.industry-page--embed) .container {
  padding-bottom: 24px;
}

.toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.stats {
  margin: 0;
  font-size: 0.82rem;
  color: #6b7280;
}

.search-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.search-icon {
  color: #9ca3af;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 0.9rem;
  color: #1f2937;
  background: transparent;
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-clear {
  flex-shrink: 0;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.search-clear:hover {
  background: #e5e7eb;
  color: #374151;
}

.layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 16px;
  align-items: stretch;
}

.layout-tree {
  min-height: 0;
  overflow-y: auto;
}

.layout-detail {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

@media (max-width: 860px) {
  .industry-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .container {
    flex: none;
    min-height: auto;
    padding-bottom: 120px;
  }

  .layout {
    flex: none;
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .layout-detail {
    min-height: 420px;
  }

  .layout-tree {
    max-height: none;
  }
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.88rem;
  cursor: pointer;
}

.btn.primary {
  background: var(--primary-color, #6366f1);
  color: #fff;
}

.btn.ghost {
  background: #fff;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.error {
  color: #dc2626;
  font-weight: 600;
  margin-bottom: 12px;
}

.muted {
  color: #6b7280;
  text-align: center;
  padding: 20px;
}
</style>
