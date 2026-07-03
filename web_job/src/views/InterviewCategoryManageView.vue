<script setup>
/**
 * 行业字典页：维护一级 / 二级行业分类。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import IndustryCategoryFormModal from "../components/interview/IndustryCategoryFormModal.vue";
import IndustryCategoryWorkspace from "../components/interview/IndustryCategoryWorkspace.vue";
import { useIndustryCategoryManage } from "../composables/useIndustryCategoryManage";
import { countIndustryCategoryTree, filterIndustryCategoryTree } from "../modules/interview/industryTreeFilter";

const route = useRoute();
const isEmbed = computed(() => route.query._embed === "1");

const selectedId = ref("");
const searchQuery = ref("");

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
} = useIndustryCategoryManage();

function updateForm(v) {
  form.value = v;
}

const level1Options = computed(() =>
  (tree.value || []).map((item) => ({
    category_id: item.category_id,
    category_name: item.category_name
  }))
);

const treeCounts = computed(() => countIndustryCategoryTree(tree.value));
const searchResult = computed(() => filterIndustryCategoryTree(tree.value, searchQuery.value));
const displayTree = computed(() => searchResult.value.items);
const searchExpandIds = computed(() => searchResult.value.expandIds);
const isSearching = computed(() => searchQuery.value.trim().length > 0);

const statsText = computed(() => {
  if (loading.value) return "加载中…";
  if (isSearching.value) return `匹配 ${searchResult.value.matchCount} 项`;
  if (tree.value.length) return `一级 ${treeCounts.value.l1} · 二级 ${treeCounts.value.l2}`;
  return "暂无分类";
});

function clearSearch() {
  searchQuery.value = "";
}

async function onSelect(categoryId) {
  selectedId.value = categoryId;
  await openDetail(categoryId);
}

async function onSubmitForm() {
  const id = await submitForm();
  if (id) selectedId.value = id;
}

function onAddChild(parentId) {
  openCreate(2, parentId);
}

async function onDelete(categoryId) {
  const removed = await removeCategory(categoryId);
  if (removed && selectedId.value === categoryId) selectedId.value = "";
}

onMounted(loadTree);
</script>

<template>
  <div v-if="isEmbed" class="category-page category-page--embed">
    <IndustryCategoryWorkspace
      v-model:search-query="searchQuery"
      :loading="loading"
      :load-error="loadError"
      :display-tree="displayTree"
      :selected-id="selectedId"
      :search-expand-ids="searchExpandIds"
      :search-keyword="isSearching ? searchQuery.trim() : ''"
      :detail="detail"
      :detail-loading="detailLoading"
      :stats-text="statsText"
      @refresh="loadTree"
      @select="onSelect"
      @edit="openEdit"
      @delete="onDelete"
      @add-child="onAddChild"
      @create-l1="openCreate(1)"
      @clear-search="clearSearch"
    />
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

  <div v-else class="home-main">
    <HomeTopBar
      title="行业字典"
      subtitle="维护一级 / 二级行业分类，供大纲与意图识别使用"
    />
    <IndustryCategoryWorkspace
      v-model:search-query="searchQuery"
      :loading="loading"
      :load-error="loadError"
      :display-tree="displayTree"
      :selected-id="selectedId"
      :search-expand-ids="searchExpandIds"
      :search-keyword="isSearching ? searchQuery.trim() : ''"
      :detail="detail"
      :detail-loading="detailLoading"
      :stats-text="statsText"
      @refresh="loadTree"
      @select="onSelect"
      @edit="openEdit"
      @delete="onDelete"
      @add-child="onAddChild"
      @create-l1="openCreate(1)"
      @clear-search="clearSearch"
    />
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
.category-page--embed {
  min-height: 100dvh;
  padding: 10px 12px 24px;
  background: var(--home-bg-accent);
}
</style>
