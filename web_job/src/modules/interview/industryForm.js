/**
 * 行业分类表单默认值与校验（纯逻辑，无 DOM）。
 */

/** @returns {import('./industryTypes').IndustryCategoryForm} */
export function emptyIndustryForm(level = 1, parentId = "") {
  return {
    category_id: "",
    parent_id: parentId,
    level,
    category_code: "",
    category_name: "",
    description: "",
    intent_keywords: "",
    enabled_for_intent: true,
    enabled_for_classify: true,
    sort_no: 0,
    status: "active"
  };
}

/** 详情 API 行 → 表单 */
export function detailToForm(detail) {
  return {
    category_id: detail.category_id || "",
    parent_id: detail.parent_id || "",
    level: detail.level ?? 1,
    category_code: detail.category_code || "",
    category_name: detail.category_name || "",
    description: detail.description || "",
    intent_keywords: detail.intent_keywords || "",
    enabled_for_intent: detail.enabled_for_intent !== false,
    enabled_for_classify: detail.enabled_for_classify !== false,
    sort_no: detail.sort_no ?? 0,
    status: detail.status || "active"
  };
}

/** 表单 → 提交 payload（编辑时不传 category_id 变更） */
export function formToPayload(form, { isEdit = false } = {}) {
  const payload = {
    parent_id: form.level === 2 ? form.parent_id : null,
    level: form.level,
    category_code: form.category_code.trim(),
    category_name: form.category_name.trim(),
    description: form.description.trim(),
    intent_keywords: form.intent_keywords.trim(),
    enabled_for_intent: !!form.enabled_for_intent,
    enabled_for_classify: !!form.enabled_for_classify,
    sort_no: Number(form.sort_no) || 0,
    status: form.status || "active"
  };
  if (!isEdit && form.category_id.trim()) {
    payload.category_id = form.category_id.trim();
  }
  return payload;
}

/** @returns {string|null} 错误文案 */
export function validateIndustryForm(form) {
  if (!form.category_code?.trim()) return "请填写编码";
  if (!form.category_name?.trim()) return "请填写名称";
  if (form.level === 2 && !form.parent_id) return "二级分类需选择所属一级";
  return null;
}
