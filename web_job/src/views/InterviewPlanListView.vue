<script setup>
/**
 * 题目大纲页：左侧二级行业树 + 右侧大纲 CRUD。
 */
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import IndustryCategoryTreeList from "../components/interview/IndustryCategoryTreeList.vue";
import InterviewPlanFormModal from "../components/interview/InterviewPlanFormModal.vue";
import InterviewPlanManagePanel from "../components/interview/InterviewPlanManagePanel.vue";
import { useInterviewPlanManage } from "../composables/useInterviewPlanManage";

const route = useRoute();
const isEmbed = computed(() => route.query._embed === "1");

const manage = useInterviewPlanManage();
const {
  industryLoading,
  industryError,
  searchQuery,
  displayTree,
  searchExpandIds,
  isSearching,
  selectedIndustryId,
  selectedIndustry,
  plans,
  plansLoading,
  plansError,
  formVisible,
  formMode,
  form,
  formError,
  formSuccess,
  formLoading,
  saving,
  guest,
  loadIndustryTree,
  selectIndustry,
  openCreate,
  openEdit,
  closeForm,
  submitForm,
  removePlan,
  clearSearch
} = manage;

function updateForm(v) {
  formSuccess.value = "";
  form.value = v;
}

async function onSubmitForm() {
  await submitForm();
}

onMounted(loadIndustryTree);
</script>

<template>
  <div class="plan-page" :class="{ 'plan-page--embed': isEmbed }">
    <section class="hero">
      <h1>面试大纲</h1>
      <p>选择左侧<strong>二级行业</strong>，管理该行业下绑定的题目大纲。</p>
    </section>

    <div class="container">
      <div v-if="!industryLoading && !industryError" class="search-bar">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          v-model="searchQuery"
          type="search"
          class="search-input"
          placeholder="搜索行业名称、编码…"
          autocomplete="off"
        />
        <button v-if="searchQuery" type="button" class="search-clear" @click="clearSearch">清除</button>
      </div>

      <p v-if="industryError" class="error">{{ industryError }}</p>
      <p v-else-if="industryLoading" class="muted">加载行业分类…</p>

      <div v-else class="layout">
        <IndustryCategoryTreeList
          class="layout-tree"
          readonly
          :selectable-level="2"
          :tree="displayTree"
          :selected-id="selectedIndustryId"
          :auto-expand-ids="searchExpandIds"
          :search-keyword="isSearching ? searchQuery.trim() : ''"
          @select="selectIndustry"
        />
        <InterviewPlanManagePanel
          class="layout-plans"
          :industry="selectedIndustry"
          :plans="plans"
          :loading="plansLoading"
          :error="plansError"
          :guest="guest"
          @create="openCreate"
          @edit="openEdit"
          @delete="removePlan"
        />
      </div>
    </div>

    <InterviewPlanFormModal
      :visible="formVisible"
      :mode="formMode"
      :form="form"
      :industry-path="selectedIndustry?.path || ''"
      :error="formError"
      :success="formSuccess"
      :loading="formLoading"
      :saving="saving"
      @close="closeForm"
      @submit="onSubmitForm"
      @update:form="updateForm"
    />
  </div>
</template>

<style scoped>
.plan-page {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 220px);
}

.plan-page--embed .hero {
  padding: 12px 16px 8px;
}

.plan-page--embed .hero h1 {
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
  color: #6b7280;
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

.toolbar {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-bottom: 12px;
}

.link-chat,
.link-muted {
  font-size: 0.88rem;
  text-decoration: none;
}

.link-chat {
  color: #6366f1;
  font-weight: 600;
}

.link-muted {
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
}

.search-icon {
  color: #9ca3af;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 0.9rem;
  background: transparent;
}

.search-clear {
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 16px;
}

.layout-tree,
.layout-plans {
  min-height: 0;
  overflow-y: auto;
}

.error {
  color: #dc2626;
  font-weight: 600;
}

.muted {
  color: #6b7280;
  text-align: center;
  padding: 20px;
}

@media (max-width: 860px) {
  .plan-page {
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
    grid-template-columns: 1fr;
  }

  .layout-plans {
    min-height: 360px;
  }
}
</style>
