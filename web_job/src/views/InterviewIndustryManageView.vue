<script setup>
/**
 * 面试分类页：侧栏壳层 + 顶栏 + 左行业树右大纲列表（与面试大纲相同能力）。
 */
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import InterviewPlanDetailModal from "../components/interview/InterviewPlanDetailModal.vue";
import InterviewPlanFormModal from "../components/interview/InterviewPlanFormModal.vue";
import InterviewPlanWorkspace from "../components/interview/InterviewPlanWorkspace.vue";
import { useInterviewPlanManage } from "../composables/useInterviewPlanManage";

const route = useRoute();
const router = useRouter();
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
  detailVisible,
  detail,
  detailLoading,
  detailError,
  loadIndustryTree,
  selectIndustry,
  openCreate,
  openEdit,
  openDetail,
  switchDetailVersion,
  closeDetail,
  editFromDetail,
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

async function openDetailFromQuery() {
  const planId = String(route.query.planId || route.query.plan || "").trim();
  if (!planId) return;
  const version = route.query.version ? Number(route.query.version) : undefined;
  await openDetail(planId, version);
  const nextQuery = { ...route.query };
  delete nextQuery.planId;
  delete nextQuery.plan;
  delete nextQuery.version;
  router.replace({ path: route.path, query: nextQuery });
}

onMounted(async () => {
  await loadIndustryTree();
  await openDetailFromQuery();
});
</script>

<template>
  <div v-if="isEmbed" class="interview-page interview-page--embed">
    <InterviewPlanWorkspace
      v-model:search-query="searchQuery"
      :industry-loading="industryLoading"
      :industry-error="industryError"
      :display-tree="displayTree"
      :selected-industry-id="selectedIndustryId"
      :search-expand-ids="searchExpandIds"
      :search-keyword="isSearching ? searchQuery.trim() : ''"
      :selected-industry="selectedIndustry"
      :plans="plans"
      :plans-loading="plansLoading"
      :plans-error="plansError"
      :guest="guest"
      hint-text="选择左侧二级行业，管理该行业下的题目大纲。"
      @refresh="loadIndustryTree"
      @select-industry="selectIndustry"
      @clear-search="clearSearch"
      @create="openCreate"
      @detail="openDetail"
      @edit="openEdit"
      @delete="removePlan"
    />
    <InterviewPlanDetailModal
      :visible="detailVisible"
      :detail="detail"
      :loading="detailLoading"
      :error="detailError"
      :guest="guest"
      @close="closeDetail"
      @edit="editFromDetail"
      @version-change="switchDetailVersion"
    />
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

  <div v-else class="home-main">
      <HomeTopBar
        title="面试分类"
        subtitle="选择左侧二级行业，查看与管理该行业下的题目大纲"
      />

      <InterviewPlanWorkspace
        v-model:search-query="searchQuery"
        :industry-loading="industryLoading"
        :industry-error="industryError"
        :display-tree="displayTree"
        :selected-industry-id="selectedIndustryId"
        :search-expand-ids="searchExpandIds"
        :search-keyword="isSearching ? searchQuery.trim() : ''"
        :selected-industry="selectedIndustry"
        :plans="plans"
        :plans-loading="plansLoading"
        :plans-error="plansError"
        :guest="guest"
        @refresh="loadIndustryTree"
        @select-industry="selectIndustry"
        @clear-search="clearSearch"
        @create="openCreate"
        @detail="openDetail"
        @edit="openEdit"
        @delete="removePlan"
      />

    <InterviewPlanDetailModal
      :visible="detailVisible"
      :detail="detail"
      :loading="detailLoading"
      :error="detailError"
      :guest="guest"
      @close="closeDetail"
      @edit="editFromDetail"
      @version-change="switchDetailVersion"
    />
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
.interview-page--embed {
  min-height: 100dvh;
  padding: 10px 12px 24px;
  background: var(--home-bg-accent);
}
</style>
