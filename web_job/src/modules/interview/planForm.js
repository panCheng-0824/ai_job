/**
 * 题目大纲表单默认值、校验与 payload 转换。
 */

/** @returns {object} 空表单 */
export function emptyPlanForm(industryCategoryId = "") {
  return {
    plan_id: "",
    industry_category_id: industryCategoryId,
    title: "",
    target_role: "",
    introduction: "",
    suitable_audience: "",
    status: "draft",
    module_tags: "",
    questions: [emptyQuestion(0)]
  };
}

export function emptyQuestion(index = 0) {
  return {
    question_id: `q${String(index + 1).padStart(3, "0")}`,
    text: "",
    weight: 1,
    thinking_hint: ""
  };
}

/** API 详情 → 表单 */
export function detailToPlanForm(detail) {
  const questions = (detail.questions || []).map((q, i) => ({
    question_id: q.question_id || `q${String(i + 1).padStart(3, "0")}`,
    text: q.text || "",
    weight: q.weight ?? 1,
    thinking_hint: q.thinking_hint || ""
  }));
  return {
    plan_id: detail.plan_id || "",
    version: detail.version ?? null,
    industry_category_id: detail.industry_category_id || "",
    title: detail.title || "",
    target_role: detail.target_role || "",
    introduction: detail.introduction || "",
    suitable_audience: detail.suitable_audience || "",
    status: detail.status || "draft",
    module_tags: (detail.module_tags || []).join(", "),
    questions: questions.length ? questions : [emptyQuestion(0)]
  };
}

/** 表单 → 提交 payload */
export function formToPlanPayload(form, studentId) {
  const tags = String(form.module_tags || "")
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean);
  const questions = (form.questions || [])
    .filter((q) => q.text?.trim())
    .map((q, i) => ({
      question_id: q.question_id?.trim() || `q${String(i + 1).padStart(3, "0")}`,
      text: q.text.trim(),
      weight: Number(q.weight) || 1,
      thinking_hint: (q.thinking_hint || "").trim(),
      timeout_seconds: 300
    }));
  const payload = {
    student_id: studentId,
    industry_category_id: form.industry_category_id,
    title: form.title.trim(),
    target_role: form.target_role.trim(),
    introduction: form.introduction.trim(),
    suitable_audience: form.suitable_audience.trim(),
    status: form.status || "draft",
    module_tags: tags,
    questions
  };
  if (form.plan_id?.trim()) payload.plan_id = form.plan_id.trim();
  return payload;
}

/** @returns {string|null} */
export function validatePlanForm(form) {
  if (!form.industry_category_id) return "请选择二级行业";
  if (!form.title?.trim()) return "请填写大纲标题";
  const validQs = (form.questions || []).filter((q) => q.text?.trim());
  if (!validQs.length) return "至少需要一道题目";
  return null;
}
