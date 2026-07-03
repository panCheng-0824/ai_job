/**
 * 学生合并画像：GET/PUT /api/me/profile
 */
import { computed, ref } from "vue";
import { apiGetFresh, apiPostForm, apiPut, getStudentId, invalidateCache } from "../api/client";
import { setStudentServerAvatar } from "./useStudentAvatar";

export const PROFILE_SEC = Object.freeze({
  student: "学生基本信息",
  family: "家庭信息",
  award: "奖励信息",
  counseling: "心理咨询申请",
  counselor: "心理咨询概要",
  tracking: "心理咨询归档",
  jobIntent: "求职意向",
  ability: "能力画像"
});

const RADAR_LABELS = ["专业能力", "沟通能力", "办公技能", "综合素养", "实践能力"];

/** 上传头像至服务端并同步全站展示（与学生画像一致） */
export async function uploadStudentAvatar(file, studentId, hooks = {}) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) throw new Error("未登录");
  if (!file) throw new Error("请选择头像文件");
  hooks.onSaving?.(true);
  hooks.onError?.("");
  try {
    const q = new URLSearchParams({ student_id: sid });
    const fd = new FormData();
    fd.append("file", file);
    const data = await apiPostForm(`/api/me/profile/avatar?${q}`, fd);
    if (data?.profile) {
      hooks.onProfileLoaded?.(data.profile);
    } else {
      const fresh = await apiGetFresh(`/api/me/profile?${q}`);
      hooks.onProfileLoaded?.(fresh);
    }
    invalidateCache("/api/me/profile");
    invalidateCache(`/api/students/${sid}`);
    const url = data?.avatar_url || data?.profile?.[PROFILE_SEC.student]?.["头像"] || "";
    setStudentServerAvatar(url, sid);
    return url;
  } catch (err) {
    const msg = err.message || "头像上传失败";
    hooks.onError?.(msg);
    throw err;
  } finally {
    hooks.onSaving?.(false);
  }
}

export function useStudentProfile() {
  const profile = ref(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref("");

  const studentInfo = computed(() => profile.value?.[PROFILE_SEC.student] || {});
  const awardInfoList = computed(() => profile.value?.[PROFILE_SEC.award] || []);
  const jobIntent = computed(() => profile.value?.[PROFILE_SEC.jobIntent] || {});
  const abilityProfile = computed(() => profile.value?.[PROFILE_SEC.ability] || {});

  const queryText = computed(() => String(jobIntent.value["综合诉求"] || "").trim());

  const abilityTags = computed(() => {
    const tags = abilityProfile.value["标签"];
    return Array.isArray(tags) ? tags.filter(Boolean) : [];
  });

  const suggestedTags = computed(() => {
    const tags = abilityProfile.value["推荐标签"];
    return Array.isArray(tags) ? tags.filter(Boolean) : [];
  });

  const radarValues = computed(() => {
    const radar = abilityProfile.value["雷达"] || {};
    return RADAR_LABELS.map((label) => {
      const n = Number(radar[label]);
      return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : 72;
    });
  });

  const intentDisplayText = computed(() => {
    const roles = jobIntent.value["意向岗位"];
    const cities = jobIntent.value["意向城市"];
    const parts = [];
    if (Array.isArray(roles) && roles.length) parts.push(roles.join("、"));
    if (Array.isArray(cities) && cities.length) parts.push(cities.join("、"));
    const salary = jobIntent.value["期望薪资"];
    if (salary && salary !== "面议") parts.push(salary);
    if (queryText.value) return queryText.value;
    return parts.join(" · ") || "待完善求职意向";
  });

  async function loadProfile(studentId) {
    const sid = String(studentId || getStudentId() || "").trim();
    if (!sid) return null;
    loading.value = true;
    error.value = "";
    try {
      const q = new URLSearchParams({ student_id: sid });
      profile.value = await apiGetFresh(`/api/me/profile?${q}`);
      setStudentServerAvatar(profile.value?.[PROFILE_SEC.student]?.["头像"], sid);
      return profile.value;
    } catch (err) {
      error.value = err.message || "加载画像失败";
      profile.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function saveSection(section, payload, studentId) {
    const sid = String(studentId || getStudentId() || "").trim();
    if (!sid) throw new Error("未登录");
    saving.value = true;
    error.value = "";
    try {
      const q = new URLSearchParams({ student_id: sid });
      const body = { [section]: payload };
      profile.value = await apiPut(`/api/me/profile?${q}`, body);
      invalidateCache("/api/me/profile");
      invalidateCache(`/api/students/${sid}`);
      return profile.value;
    } catch (err) {
      error.value = err.message || "保存失败";
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function uploadAvatar(file, studentId) {
    return uploadStudentAvatar(file, studentId, {
      onProfileLoaded: (nextProfile) => {
        profile.value = nextProfile;
      },
      onSaving: (v) => {
        saving.value = v;
      },
      onError: (msg) => {
        error.value = msg;
      }
    });
  }

  /** 将匹配诉求同步回画像（仅更新 queryText，静默失败） */
  async function syncQueryText(text, studentId) {
    const q = String(text || "").trim();
    if (!q || q === queryText.value) return;
    try {
      await saveJobIntent({ queryText: q }, studentId);
    } catch {
      /* 匹配流程不阻断 */
    }
  }

  /** 供简历页导入：从画像求职意向映射到 resume intent */
  function jobIntentToResumeIntent(source = jobIntent.value) {
    const roles = source["意向岗位"];
    const companies = source["意向企业"];
    const cities = source["意向城市"];
    const salary = source["期望薪资"];
    const query = source["综合诉求"];
    const parts = [];
    if (Array.isArray(roles) && roles.length) parts.push(roles.join("、"));
    if (Array.isArray(cities) && cities.length) parts.push(`城市：${cities.join("、")}`);
    if (salary && salary !== "面议") parts.push(`薪资：${salary}`);
    if (query) parts.push(query);
    return {
      targetJobs: Array.isArray(roles) && roles.length ? roles.join("、") : String(query || "").trim(),
      targetCompanies: Array.isArray(companies) ? companies.join("、") : ""
    };
  }

  function saveContact(contact) {
    return saveSection("contact", contact);
  }

  function saveJobIntent(intent) {
    return saveSection("job_intent", intent);
  }

  function saveAbility(ability) {
    return saveSection("ability", ability);
  }

  /** 从 API 求职意向段构建编辑表单初始值 */
  function jobIntentToForm(source = jobIntent.value) {
    return {
      targetRoles: [...(source["意向岗位"] || [])],
      targetCities: [...(source["意向城市"] || [])],
      targetCompanies: [...(source["意向企业"] || [])],
      salaryMin: source.salaryMin ?? null,
      salaryMax: source.salaryMax ?? null,
      salaryNegotiable: source.salaryNegotiable !== false && source["期望薪资"] === "面议"
        ? true
        : Boolean(source.salaryNegotiable ?? source["salaryNegotiable"]),
      queryText: source["综合诉求"] || ""
    };
  }

  function abilityToForm(source = abilityProfile.value) {
    const raw = source.radarRaw || {};
    return {
      tags: [...(source["标签"] || [])],
      radar: {
        professional: Number(raw.professional ?? source["雷达"]?.["专业能力"] ?? 72),
        communication: Number(raw.communication ?? source["雷达"]?.["沟通能力"] ?? 72),
        office: Number(raw.office ?? source["雷达"]?.["办公技能"] ?? 72),
        comprehensive: Number(raw.comprehensive ?? source["雷达"]?.["综合素养"] ?? 72),
        practice: Number(raw.practice ?? source["雷达"]?.["实践能力"] ?? 72)
      }
    };
  }

  function contactToForm(source = studentInfo.value) {
    return {
      phone: source["手机"] || "",
      email: source["邮箱"] || "",
      campus_experience: source["校园经历补充"] || ""
    };
  }

  return {
    profile,
    loading,
    saving,
    error,
    studentInfo,
    awardInfoList,
    jobIntent,
    abilityProfile,
    queryText,
    abilityTags,
    suggestedTags,
    radarValues,
    intentDisplayText,
    loadProfile,
    saveContact,
    saveJobIntent,
    saveAbility,
    uploadAvatar,
    syncQueryText,
    jobIntentToResumeIntent,
    jobIntentToForm,
    abilityToForm,
    contactToForm
  };
}
