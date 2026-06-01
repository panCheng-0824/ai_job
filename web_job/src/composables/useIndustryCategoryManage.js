/**
 * 行业分类管理页组合式逻辑：列表、详情、表单弹层、CRUD。
 */
import { ref } from "vue";
import {
  createIndustryCategory,
  deleteIndustryCategory,
  fetchIndustryCategories,
  fetchIndustryCategoryDetail,
  updateIndustryCategory
} from "../modules/interview/api";
import { detailToForm, emptyIndustryForm, formToPayload, validateIndustryForm } from "../modules/interview/industryForm";

export function useIndustryCategoryManage() {
  const tree = ref([]);
  const loadError = ref("");
  const loading = ref(false);
  const detail = ref(null);
  const detailLoading = ref(false);
  const formVisible = ref(false);
  const formMode = ref("create");
  const form = ref(emptyIndustryForm(1));
  const formError = ref("");
  const saving = ref(false);

  async function loadTree() {
    loading.value = true;
    loadError.value = "";
    try {
      const resp = await fetchIndustryCategories({ tree: true, includeAll: true });
      tree.value = resp.items || [];
    } catch (e) {
      loadError.value = e.message || "加载失败";
      tree.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function openDetail(categoryId) {
    detailLoading.value = true;
    detail.value = null;
    try {
      detail.value = await fetchIndustryCategoryDetail(categoryId);
    } catch (e) {
      loadError.value = e.message || "加载详情失败";
    } finally {
      detailLoading.value = false;
    }
  }

  function openCreate(level, parentId = "") {
    formMode.value = "create";
    form.value = emptyIndustryForm(level, parentId);
    formError.value = "";
    formVisible.value = true;
  }

  async function openEdit(categoryId) {
    formMode.value = "edit";
    formError.value = "";
    try {
      const d = await fetchIndustryCategoryDetail(categoryId);
      form.value = detailToForm(d);
      formVisible.value = true;
    } catch (e) {
      formError.value = e.message || "加载失败";
    }
  }

  function closeForm() {
    formVisible.value = false;
    formError.value = "";
  }

  async function submitForm() {
    const err = validateIndustryForm(form.value);
    if (err) {
      formError.value = err;
      return null;
    }
    saving.value = true;
    formError.value = "";
    try {
      const payload = formToPayload(form.value, { isEdit: formMode.value === "edit" });
      if (formMode.value === "edit") {
        await updateIndustryCategory(form.value.category_id, payload);
        formVisible.value = false;
        await loadTree();
        await openDetail(form.value.category_id);
        return form.value.category_id;
      }
      const res = await createIndustryCategory(payload);
      formVisible.value = false;
      await loadTree();
      if (res.category_id) {
        await openDetail(res.category_id);
      }
      return res.category_id || null;
    } catch (e) {
      formError.value = e.message || "保存失败";
      return null;
    } finally {
      saving.value = false;
    }
  }

  async function removeCategory(categoryId) {
    if (!globalThis.confirm("确定删除该行业分类？此操作不可恢复。")) return;
    try {
      await deleteIndustryCategory(categoryId);
      if (detail.value?.category_id === categoryId) detail.value = null;
      await loadTree();
      return categoryId;
    } catch (e) {
      loadError.value = e.message || "删除失败";
      return null;
    }
  }

  return {
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
  };
}
