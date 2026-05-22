/** 与学生画像接口字段对齐：StudentView 中 SEC.student = "学生基本信息" */
export const STUDENT_SECTION_KEY = "学生基本信息";

/**
 * 将学生画像中的「学生基本信息」映射为简历基础字段（可再编辑）。
 * @param {Record<string, any> | null | undefined} portrait
 * @returns {Record<string, string>}
 */
export function prefillBasicFromPortrait(portrait) {
  const s = portrait?.[STUDENT_SECTION_KEY] || {};
  const grad = [s["毕业年度"], s["毕业季节"]].filter(Boolean).join("");
  return {
    姓名: String(s["姓名"] ?? "").trim(),
    学号: String(s["学号"] ?? "").trim(),
    手机: "",
    邮箱: "",
    学校: String(s["学校名称"] ?? "").trim(),
    院系: String(s["院系名称"] ?? "").trim(),
    专业: String(s["专业名称"] ?? "").trim(),
    班级: String(s["班级名称"] ?? "").trim(),
    学历: String(s["学历"] ?? "").trim(),
    毕业时间: grad,
    籍贯: "",
    通信地址: ""
  };
}

export { emptySectionsForTemplate } from "./sectionsModel";
