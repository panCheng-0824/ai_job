/**
 * 面试大纲页：二级行业选择 + 大纲 CRUD。
 */
import { computed, ref } from "vue";
import { getStudentId } from "../api/client";
import {
  createInterviewPlan,
  deleteInterviewPlan,
  fetchIndustryCategories,
  fetchInterviewPlanDetail,
  fetchInterviewPlans,
  reviseInterviewPlan
} from "../modules/interview/api";
import { findIndustryCategory } from "../modules/interview/industryCategoryLookup";
import { filterIndustryCategoryTree } from "../modules/interview/industryTreeFilter";
import { detailToPlanForm, emptyPlanForm, formToPlanPayload, validatePlanForm } from "../modules/interview/planForm";

export function useInterviewPlanManage() {
  const industryTree = ref([]);
  const industryLoading = ref(false);
  const industryError = ref("");
  const searchQuery = ref("");

  const selectedIndustryId = ref("");
  const plans = ref([]);
  const plansLoading = ref(false);
  const plansError = ref("");

  const formVisible = ref(false);
  const formMode = ref("create");
  const form = ref(emptyPlanForm());
  const formError = ref("");
  const formSuccess = ref("");
  const formLoading = ref(false);
  const saving = ref(false);
  const guest = ref(false);

  const searchResult = computed(() => filterIndustryCategoryTree(industryTree.value, searchQuery.value));
  const displayTree = computed(() => searchResult.value.items);
  const searchExpandIds = computed(() => searchResult.value.expandIds);
  const isSearching = computed(() => searchQuery.value.trim().length > 0);

  const selectedIndustry = computed(() => {
    const cat = findIndustryCategory(industryTree.value, selectedIndustryId.value);
    if (!cat || cat.level !== 2) return null;
    return cat;
  });

  async function loadIndustryTree() {
    industryLoading.value = true;
    industryError.value = "";
    try {
      const resp = await fetchIndustryCategories({ tree: true, includeAll: false });
      industryTree.value = resp.items || [];
    } catch (e) {
      industryError.value = e.message || "行业分类加载失败";
      industryTree.value = [];
    } finally {
      industryLoading.value = false;
    }
  }

  async function loadPlans() {
    const sid = getStudentId();
    guest.value = !sid;
    if (!sid || !selectedIndustryId.value || selectedIndustry.value?.level !== 2) {
      plans.value = [];
      plansError.value = "";
      return;
    }
    plansLoading.value = true;
    plansError.value = "";
    try {
      const resp = await fetchInterviewPlans(sid, { industryCategoryId: selectedIndustryId.value });
      plans.value = resp.items || [];
    } catch (e) {
      plansError.value = e.message || "大纲加载失败";
      plans.value = [];
    } finally {
      plansLoading.value = false;
    }
  }

  /** 仅二级行业触发选中与加载 */
  async function selectIndustry(categoryId) {
    const cat = findIndustryCategory(industryTree.value, categoryId);
    if (!cat || cat.level !== 2) {
      selectedIndustryId.value = "";
      plans.value = [];
      return;
    }
    selectedIndustryId.value = categoryId;
    await loadPlans();
  }

  function openCreate() {
    if (!selectedIndustry.value) return;
    formMode.value = "create";
    form.value = emptyPlanForm(selectedIndustryId.value);
    formError.value = "";
    formSuccess.value = "";
    formVisible.value = true;
  }

  async function openEdit(planId, version) {
    const sid = getStudentId();
    if (!sid) return;
    formMode.value = "edit";
    formError.value = "";
    formSuccess.value = "";
    formVisible.value = true;
    formLoading.value = true;
    form.value = emptyPlanForm(selectedIndustryId.value);
    try {
      const detail = await fetchInterviewPlanDetail(sid, planId, version);
      form.value = detailToPlanForm(detail);
    } catch (e) {
      formVisible.value = false;
      plansError.value = e.message || "加载大纲失败";
    } finally {
      formLoading.value = false;
    }
  }

  function closeForm() {
    formVisible.value = false;
    formError.value = "";
    formSuccess.value = "";
  }

  /** 编辑升版保存后：拉取最新版本详情回填表单 */
  async function reloadEditForm(sid, planId, version) {
    formLoading.value = true;
    try {
      const detail = await fetchInterviewPlanDetail(sid, planId, version);
      form.value = detailToPlanForm(detail);
      formSuccess.value = `已保存，当前版本 v${detail.version}`;
    } finally {
      formLoading.value = false;
    }
  }

  async function submitForm() {
    const sid = getStudentId();
    if (!sid) {
      formError.value = "请先登录";
      formSuccess.value = "";
      return false;
    }
    const err = validatePlanForm(form.value);
    if (err) {
      formError.value = err;
      formSuccess.value = "";
      return false;
    }
    saving.value = true;
    formError.value = "";
    formSuccess.value = "";
    try {
      const payload = formToPlanPayload(form.value, sid);
      if (formMode.value === "edit") {
        const planId = form.value.plan_id;
        const res = await reviseInterviewPlan(planId, payload);
        await loadPlans();
        await reloadEditForm(sid, planId, res.version);
        return true;
      }
      await createInterviewPlan(payload);
      formVisible.value = false;
      await loadPlans();
      return true;
    } catch (e) {
      formError.value = e.message || "保存失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function removePlan(planId) {
    const sid = getStudentId();
    if (!sid || !globalThis.confirm("确定删除该题目大纲？此操作不可恢复。")) return;
    try {
      await deleteInterviewPlan(sid, planId);
      await loadPlans();
    } catch (e) {
      plansError.value = e.message || "删除失败";
    }
  }

  function clearSearch() {
    searchQuery.value = "";
  }

  return {
    industryTree,
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
    loadPlans,
    openCreate,
    openEdit,
    closeForm,
    submitForm,
    removePlan,
    clearSearch
  };
}
