<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRaw, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet } from "../api/client";
import { useStudentAvatar, setStudentServerAvatar } from "../composables/useStudentAvatar";
import { uploadStudentAvatar } from "../composables/useStudentProfile";
import ResumeCopyModal from "../components/resume/ResumeCopyModal.vue";
import ResumeEditorSheet from "../components/resume/ResumeEditorSheet.vue";
import ResumeStudioLayout from "../components/resume/ResumeStudioLayout.vue";
import ResumeTemplateSidebar from "../components/resume/ResumeTemplateSidebar.vue";
import ResumeTemplateStrip from "../components/resume/ResumeTemplateStrip.vue";
import ResumeVersionPreviewPanel from "../components/resume/ResumeVersionPreviewPanel.vue";
import ResumeAiOptimizeRail from "../components/resume/ResumeAiOptimizeRail.vue";
import { buildBasicForSave, parseResumeContent } from "../modules/resume/content";
import { emptySectionsForTemplate, prefillBasicFromPortrait } from "../modules/resume/prefill";
import { normalizeSectionItems, serializeSections } from "../modules/resume/sectionsModel";
import {
  RESUME_TEMPLATES,
  getTemplateById,
  mapSectionsOnTemplateChange
} from "../modules/resume/templates";
import {
  appendTimeCopySuffix,
  appendVersionSnapshot,
  deleteResume,
  insertNewResumeRecord,
  loadStore,
  newResumeId,
  nextDisplayName,
  pickSeriesDefaultVersion,
  setDefaultResume,
  stripTimeCopySuffix,
  updateResumeInPlace
} from "../modules/resume/storage";
import * as resumeApi from "../modules/resume/api";
import {
  resumeStudioRailVisibleRef as studioRailVisible,
  setResumeStudioRailVisible
} from "../composables/useResumeStudioRailVisible";
import {
  resumeAiRailVisibleRef as aiRailVisible,
  setResumeAiRailVisible
} from "../composables/useResumeAiRailVisible";
import { subscribeResumeRender } from "../composables/useResumeRenderBridge";
import { dispatchResumeAiContext } from "../composables/useResumeAiContextBridge";
import { mergeResumeRenderIntoEditor } from "../modules/resume/applyRenderPayload";
import {
  buildResumeDocumentModel,
  buildResumeDocumentModelFromRecord,
  exportResumeByFormat
} from "../modules/resume/exportDocument";
import { formatResumePreviewText } from "../modules/resume/previewText";
import { maskName, maskStudentField } from "../utils/studentDesensitize";

const route = useRoute();
const isEmbed = computed(() => route.query._embed === "1");
const { avatarUrl: sharedAvatarUrl } = useStudentAvatar();

const error = ref("");
const loadingStudent = ref(false);
const studentPortrait = ref(null);

const draftId = ref(null);
const selectedTemplateId = ref(RESUME_TEMPLATES[0].id);
const displayName = ref("");
const basic = ref(prefillBasicFromPortrait(null));
const intent = ref({ targetJobs: "", targetCompanies: "" });
const sections = ref(emptySectionsForTemplate(getTemplateById(selectedTemplateId.value)));
const extraNotes = ref("");

const seriesId = ref(null);
const resumeStore = ref(loadStore());

const copyModalOpen = ref(false);
const copyModalGroup = ref(null);
/** 与首页 StudentAvatar 一致：画像头像优先，其次全站共享 ref / localStorage */
const avatarUrl = computed(() => {
  const fromPortrait = studentPortrait.value?.["学生基本信息"]?.["头像"]?.trim();
  if (fromPortrait) return fromPortrait;
  return sharedAvatarUrl.value;
});

const TEMPLATES_PANEL_KEY = "resume_templates_panel_open";

function readTemplatesPanelOpen() {
  try {
    return localStorage.getItem(TEMPLATES_PANEL_KEY) !== "0";
  } catch {
    return true;
  }
}

const templatesPanelOpen = ref(readTemplatesPanelOpen());

watch(templatesPanelOpen, (open) => {
  try {
    localStorage.setItem(TEMPLATES_PANEL_KEY, open ? "1" : "0");
  } catch {
    /* ignore */
  }
});

const BASIC_INFO_KEYS = ["学号", "姓名", "学校", "院系", "专业", "班级", "学历", "毕业时间", "籍贯"];
const CONTACT_INFO_KEYS = ["手机", "邮箱", "通信地址"];

const showRightRail = computed(() => studioRailVisible.value || aiRailVisible.value);

const activeRightPanel = computed(() => {
  if (studioRailVisible.value) return "version";
  if (aiRailVisible.value) return "ai";
  return null;
});

const drawerTitle = computed(() => {
  if (activeRightPanel.value === "version") return "版本预览";
  if (activeRightPanel.value === "ai") return "AI 优化";
  return "";
});

const sectionEditMode = ref({ basic: false, contact: false, intent: false });

function toggleEditSection(key) {
  sectionEditMode.value[key] = !sectionEditMode.value[key];
}

function closeRightPanel() {
  setResumeStudioRailVisible(false);
  setResumeAiRailVisible(false);
}

function toggleVersionPanel() {
  if (studioRailVisible.value) {
    setResumeStudioRailVisible(false);
    return;
  }
  setResumeAiRailVisible(false);
  setResumeStudioRailVisible(true);
}

function toggleAiPanel() {
  if (aiRailVisible.value) {
    setResumeAiRailVisible(false);
    return;
  }
  setResumeStudioRailVisible(false);
  setResumeAiRailVisible(true);
}

function openVersionPanel() {
  setResumeAiRailVisible(false);
  setResumeStudioRailVisible(true);
}

function openAiPanel() {
  setResumeStudioRailVisible(false);
  setResumeAiRailVisible(true);
}

function handleTemplateUpload() {
  resumeApplyNotice.value = "请在右侧 AI 优化中使用「解析上传简历」识别文件内容。";
  openAiPanel();
}

async function handleAvatarChange(file) {
  if (!file?.type?.startsWith("image/")) return;
  try {
    await uploadStudentAvatar(file, getStudentId().trim());
    resumeApplyNotice.value = "头像已更新，与学生画像保持一致";
  } catch (e) {
    resumeApplyNotice.value = e?.message || "头像上传失败";
  }
}

/** 保存时同时设为对话/规划师引用的全局默认 */
const setAsGlobalDefault = ref(false);
const saving = ref(false);
const loadingRecord = ref(false);
const resumeApplyNotice = ref("");

const currentTemplate = computed(() => getTemplateById(selectedTemplateId.value));

const globalDefaultId = computed(() => resumeStore.value.defaultResumeId || null);

const resumeGroups = computed(() => {
  const list = resumeStore.value.resumes || [];
  const gDef = globalDefaultId.value;
  const map = new Map();
  for (const r of list) {
    const s = r.seriesId || r.id;
    if (!map.has(s)) map.set(s, []);
    map.get(s).push(r);
  }
  const groups = [];
  for (const [sidKey, versions] of map) {
    versions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    const seriesDefault = pickSeriesDefaultVersion(versions, gDef);
    const label = stripTimeCopySuffix(seriesDefault?.displayName || versions[0]?.displayName || "") || "简历";
    const isGlobalSeries = versions.some((v) => v.id === gDef);
    groups.push({
      seriesId: sidKey,
      versions,
      label,
      seriesDefaultId: seriesDefault?.id,
      isGlobalSeries
    });
  }
  groups.sort((a, b) => {
    if (a.isGlobalSeries !== b.isGlobalSeries) return a.isGlobalSeries ? -1 : 1;
    return (b.versions[0]?.updatedAt || 0) - (a.versions[0]?.updatedAt || 0);
  });
  return groups;
});

const canSaveInPlace = computed(() => !!draftId.value);

const saveHint = computed(() => {
  if (!draftId.value) {
    return "保存将创建新简历及首条记录。";
  }
  return "保存将更新当前简历，并留存修改前的版本快照。另存为会以当前内容新建一份独立简历。";
});

const currentDraftRecord = computed(() => {
  if (!draftId.value) return null;
  return (resumeStore.value.resumes || []).find((r) => r.id === draftId.value) || null;
});

const activeSeriesGroup = computed(() => {
  if (!seriesId.value) return null;
  return resumeGroups.value.find((g) => g.seriesId === seriesId.value) || null;
});

const globalDefaultRecord = computed(() => {
  const id = globalDefaultId.value;
  if (!id) return null;
  return (resumeStore.value.resumes || []).find((r) => r.id === id) || null;
});

const studentInfo = computed(() => studentPortrait.value?.["学生基本信息"] || {});

const heroName = computed(() =>
  maskName(basic.value.姓名 || studentInfo.value.姓名) || "同学"
);

const heroSubtitle = computed(() =>
  [
    maskStudentField("学校", basic.value.学校),
    maskStudentField("院系", basic.value.院系),
    maskStudentField("专业", basic.value.专业),
    maskStudentField("学历", basic.value.学历),
    basic.value.毕业时间
  ]
    .filter(Boolean)
    .join(" | ")
);

const heroPhone = computed(() => maskStudentField("手机", basic.value.手机));
const heroEmail = computed(() => maskStudentField("邮箱", basic.value.邮箱));

const studentDisplayName = computed(() =>
  maskName(basic.value.姓名 || studentInfo.value.姓名) || ""
);

const pageSubtitle = computed(() => {
  if (displayName.value.trim() && studioRailVisible.value) {
    return displayName.value.trim();
  }
  return currentTemplate.value.name;
});

const editorTitle = computed(() => {
  if (studioRailVisible.value && displayName.value.trim()) {
    return displayName.value.trim();
  }
  return currentTemplate.value.name;
});

watch(selectedTemplateId, (tid, prevTid) => {
  if (!prevTid || prevTid === tid) return;
  const fromTpl = getTemplateById(prevTid);
  const toTpl = getTemplateById(tid);
  sections.value = mapSectionsOnTemplateChange({ ...sections.value }, fromTpl, toTpl);
  resumeApplyNotice.value = `已切换为「${toTpl.name}」模板，正文已尽量保留。`;
});

let noticeTimer = null;
watch(resumeApplyNotice, (msg) => {
  if (noticeTimer) {
    clearTimeout(noticeTimer);
    noticeTimer = null;
  }
  if (!msg) return;
  noticeTimer = setTimeout(() => {
    resumeApplyNotice.value = "";
    noticeTimer = null;
  }, 7000);
});

function getStudentId() {
  return route.query.student_id || localStorage.getItem("student_id") || "";
}

function hasStudentContext() {
  return !!getStudentId().trim();
}

async function refreshStore() {
  try {
    if (hasStudentContext()) {
      resumeStore.value = await resumeApi.fetchResumeStore(getStudentId().trim());
    } else {
      resumeStore.value = loadStore();
    }
  } catch (e) {
    error.value = e.message || "加载简历列表失败";
  }
}

async function loadStudent() {
  const sid = getStudentId();
  if (!sid) return;
  loadingStudent.value = true;
  try {
    error.value = "";
    const q = new URLSearchParams({ student_id: sid });
    studentPortrait.value = await apiGet(`/api/me/profile?${q}`);
    const avatar = studentPortrait.value?.["学生基本信息"]?.["头像"];
    if (avatar?.trim()) {
      setStudentServerAvatar(avatar, sid);
    }
    if (!draftId.value && !seriesId.value) {
      basic.value = prefillBasicFromPortrait(studentPortrait.value);
    }
  } catch (e) {
    error.value = e.message || "加载学生信息失败";
  } finally {
    loadingStudent.value = false;
  }
}

function resetDraft() {
  draftId.value = null;
  seriesId.value = null;
  displayName.value = "";
  selectedTemplateId.value = RESUME_TEMPLATES[0].id;
  basic.value = prefillBasicFromPortrait(studentPortrait.value);
  intent.value = { targetJobs: "", targetCompanies: "" };
  sections.value = emptySectionsForTemplate(getTemplateById(selectedTemplateId.value));
  extraNotes.value = "";
}

/** 表单是否已有用户填写内容（不含仅来自画像的学号/姓名等预填）。 */
function formHasUserContent() {
  if (displayName.value.trim() || extraNotes.value.trim()) return true;
  if (intent.value.targetJobs?.trim() || intent.value.targetCompanies?.trim()) return true;
  const portraitBasic = prefillBasicFromPortrait(studentPortrait.value);
  for (const [k, v] of Object.entries(basic.value)) {
    if (String(v ?? "").trim() !== String(portraitBasic[k] ?? "").trim()) return true;
  }
  const tpl = currentTemplate.value;
  for (const key of tpl.sectionKeys) {
    const items = normalizeSectionItems(sections.value[key]);
    if (items.some((i) => i.title?.trim() || i.body?.trim())) return true;
  }
  return false;
}

/** 清空左侧表单（解除与已保存副本的绑定，恢复空白草稿）。 */
function clearFormData() {
  if (formHasUserContent()) {
    const ok = confirm("确定清空当前表单？未保存的修改将丢失。");
    if (!ok) return;
  }
  resetDraft();
  resumeApplyNotice.value = "";
  error.value = "";
}

function mergeRecordIntoStore(rec) {
  const store = resumeStore.value;
  const list = store.resumes || [];
  const idx = list.findIndex((r) => r.id === rec.id);
  if (idx < 0) return;
  const resumes = [...list];
  resumes[idx] = rec;
  resumeStore.value = { ...store, resumes };
}

function applyRecord(rec) {
  const content = parseResumeContent(rec?.content);
  draftId.value = rec.id;
  seriesId.value = rec.seriesId || rec.id;
  displayName.value = stripTimeCopySuffix(rec.displayName || "") || "";
  selectedTemplateId.value = rec.templateId || RESUME_TEMPLATES[0].id;
  basic.value = { ...prefillBasicFromPortrait(null), ...content.basic };
  intent.value = { ...content.intent };
  const t = getTemplateById(selectedTemplateId.value);
  sections.value = Object.fromEntries(
    t.sectionKeys.map((k) => [k, normalizeSectionItems(content.sections[k])])
  );
  extraNotes.value = content.extraNotes;
}

/** AI resume_render 事件：合并进左侧编辑器（不自动保存）。 */
function applyResumeRenderPayload(payload) {
  const parsed = parseResumeContent(payload);
  const tid = (parsed.templateId || "").trim();
  let tpl = currentTemplate.value;
  let sec = sections.value;
  if (tid && tid !== selectedTemplateId.value) {
    const fromTpl = getTemplateById(selectedTemplateId.value);
    tpl = getTemplateById(tid);
    selectedTemplateId.value = tid;
    sec = mapSectionsOnTemplateChange({ ...sec }, fromTpl, tpl);
  }
  const merged = mergeResumeRenderIntoEditor({
    payload,
    template: tpl,
    basic: basic.value,
    intent: intent.value,
    sections: sec,
    extraNotes: extraNotes.value
  });
  basic.value = merged.basic;
  intent.value = merged.intent;
  sections.value = merged.sections;
  extraNotes.value = merged.extraNotes;
  resumeApplyNotice.value = tid
    ? `AI 已按模版「${tpl.name}」更新左侧简历内容，请核对后保存。`
    : "AI 已根据生成结果更新左侧简历内容，请核对后保存。";
}

function resolveResumeId(recOrId) {
  if (typeof recOrId === "string") return recOrId.trim();
  return recOrId?.id ? String(recOrId.id) : "";
}

/** 载入副本：有学号时从服务端拉取最新 content；未登录仍用本地存储。 */
async function loadRecord(recOrId) {
  const id = resolveResumeId(recOrId);
  if (!id) return;
  loadingRecord.value = true;
  error.value = "";
  try {
    let rec;
    if (hasStudentContext()) {
      rec = await resumeApi.fetchResumeById(getStudentId().trim(), id);
      mergeRecordIntoStore(rec);
    } else {
      const store = loadStore();
      rec =
        typeof recOrId === "object" && recOrId?.content != null
          ? recOrId
          : (store.resumes || []).find((r) => r.id === id);
    }
    if (!rec) {
      error.value = "未找到该副本";
      return;
    }
    applyRecord(rec);
  } catch (e) {
    error.value = e.message || "加载简历失败";
  } finally {
    loadingRecord.value = false;
  }
}

function buildContent() {
  return {
    basic: buildBasicForSave(toRaw(basic.value)),
    intent: {
      targetJobs: String(intent.value.targetJobs ?? "").trim(),
      targetCompanies: String(intent.value.targetCompanies ?? "").trim()
    },
    sections: serializeSections(toRaw(sections.value)),
    extraNotes: extraNotes.value.trim()
  };
}

/** 当前工作副本的展示名（逻辑名，无时间戳后缀）。 */
function buildCurrentDisplayName(existing) {
  return (
    displayName.value.trim() ||
    stripTimeCopySuffix(existing?.displayName || "") ||
    "简历"
  );
}

/** 保存前将已存内容固化为历史快照 payload。 */
function buildSnapshotPayload(existing, ser) {
  const content =
    existing?.content && typeof existing.content === "object"
      ? existing.content
      : parseResumeContent(existing?.content);
  const base = stripTimeCopySuffix(existing?.displayName || "") || displayName.value.trim() || "简历";
  return {
    seriesId: ser,
    templateId: existing?.templateId || selectedTemplateId.value,
    displayName: appendTimeCopySuffix(base),
    content,
    setSeriesDefault: false,
    setGlobalDefault: false,
    createdAt: existing?.updatedAt || existing?.createdAt || Date.now()
  };
}

async function persistCreateResume(sid, resumeId, seriesKey, payload) {
  const body = {
    ...payload,
    seriesId: seriesKey,
    setSeriesDefault: true,
    setGlobalDefault: payload.setGlobalDefault ?? setAsGlobalDefault.value
  };
  if (sid) {
    resumeStore.value = await resumeApi.putResume(sid, resumeId, body);
  } else {
    const { store, seriesId: ser } = insertNewResumeRecord(
      {
        id: resumeId,
        templateId: body.templateId,
        displayName: body.displayName,
        content: body.content,
        seriesId: seriesKey,
        createdAt: body.createdAt ?? Date.now()
      },
      { setGlobalDefault: body.setGlobalDefault }
    );
    resumeStore.value = store;
    seriesId.value = ser;
  }
}

/** 无 id：新增简历；有 id：修改当前并留存修改前快照。 */
async function saveDraft() {
  const sid = getStudentId().trim();
  const store = hasStudentContext() ? resumeStore.value : loadStore();

  if (!draftId.value) {
    const ser = newResumeId();
    const newId = newResumeId();
    const name = resolveLogicalDisplayName(store);
    seriesId.value = ser;
    const payload = {
      templateId: selectedTemplateId.value,
      displayName: name,
      content: buildContent(),
      createdAt: Date.now(),
      setGlobalDefault: setAsGlobalDefault.value
    };
    saving.value = true;
    try {
      await persistCreateResume(sid, newId, ser, payload);
      draftId.value = newId;
      await loadRecord(newId);
      error.value = "";
    } catch (e) {
      error.value = e.message || "保存失败";
    } finally {
      saving.value = false;
    }
    return;
  }

  const existing = getDraftRecord();
  if (!existing) {
    draftId.value = null;
    await saveDraft();
    return;
  }

  const ser = seriesId.value || existing.seriesId || existing.id;
  seriesId.value = ser;
  const updatePayload = {
    seriesId: ser,
    templateId: selectedTemplateId.value,
    displayName: buildCurrentDisplayName(existing),
    content: buildContent(),
    setSeriesDefault: true,
    setGlobalDefault: setAsGlobalDefault.value
  };

  saving.value = true;
  try {
    if (sid) {
      const snapshotId = newResumeId();
      await persistPut(sid, snapshotId, buildSnapshotPayload(existing, ser));
      await persistPut(sid, draftId.value, updatePayload);
      await loadRecord(draftId.value);
    } else {
      appendVersionSnapshot(existing);
      resumeStore.value = updateResumeInPlace(
        {
          ...existing,
          ...updatePayload,
          id: draftId.value,
          updatedAt: Date.now()
        },
        { setGlobalDefault: setAsGlobalDefault.value }
      );
      await loadRecord(draftId.value);
    }
    error.value = "";
  } catch (e) {
    error.value = e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

/** 另存为：以当前表单内容新建一份独立简历（新 seriesId + 新逻辑名）。 */
async function saveAsNewResume() {
  const sid = getStudentId().trim();
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  const ser = newResumeId();
  const newId = newResumeId();
  const name = nextDisplayName({
    studentNo: basic.value.学号,
    name: basic.value.姓名,
    store
  });
  displayName.value = name;
  seriesId.value = ser;
  const payload = {
    templateId: selectedTemplateId.value,
    displayName: name,
    content: buildContent(),
    createdAt: Date.now(),
    setGlobalDefault: setAsGlobalDefault.value
  };
  saving.value = true;
  try {
    await persistCreateResume(sid, newId, ser, payload);
    draftId.value = newId;
    await loadRecord(newId);
    error.value = "";
  } catch (e) {
    error.value = e.message || "另存为新简历失败";
  } finally {
    saving.value = false;
  }
}

async function selectResumeGroup(g) {
  const rec = pickSeriesDefaultVersion(g.versions, globalDefaultId.value) || g.versions[0];
  if (rec) await loadRecord(rec.id);
}

function openCopyModal(g) {
  copyModalGroup.value = { ...g, versions: [...g.versions] };
  copyModalOpen.value = true;
}

async function handleSetDefault(id, scope) {
  await onSetDefault(id, scope);
  await nextTick();
  if (copyModalOpen.value) rebindCopyModalGroup();
}

function closeCopyModal() {
  copyModalOpen.value = false;
  copyModalGroup.value = null;
}

async function syncCopyFromModal(rec) {
  await loadRecord(rec);
  closeCopyModal();
}

function rebindCopyModalGroup() {
  if (!copyModalOpen.value || !copyModalGroup.value) return;
  const sid = copyModalGroup.value.seriesId;
  const fresh = resumeGroups.value.find((x) => x.seriesId === sid);
  if (!fresh || !fresh.versions.length) {
    closeCopyModal();
    return;
  }
  copyModalGroup.value = { ...fresh, versions: [...fresh.versions] };
}

async function setDefaultFromModal(id, scope) {
  await onSetDefault(id, scope);
  await nextTick();
  rebindCopyModalGroup();
}

async function deleteCopyFromModal(id) {
  await onDelete(id);
  await nextTick();
  rebindCopyModalGroup();
}

async function deleteEntireSeriesFromModal(g) {
  const label = stripTimeCopySuffix(g?.label || "该简历");
  const count = g?.versions?.length || 0;
  if (!count) return;
  if (!confirm(`确定删除「${label}」及其全部 ${count} 条副本？此操作不可恢复。`)) return;
  const ids = g.versions.map((r) => r.id);
  for (const id of ids) {
    if (hasStudentContext()) {
      try {
        resumeStore.value = await resumeApi.deleteResumeOnServer(getStudentId().trim(), id);
        if (draftId.value === id) resetDraft();
      } catch (e) {
        error.value = e.message || "删除失败";
        return;
      }
    } else {
      deleteResume(id);
      if (draftId.value === id) resetDraft();
    }
  }
  if (!hasStudentContext()) await refreshStore();
  error.value = "";
  closeCopyModal();
}

/**
 * 以左侧当前内容新开一条简历线：保留表单数据，仅解除与旧副本/旧系列的绑定；
 * 下次「保存当前」会用当前内容作为新简历的第一条副本（含新 series_id）。
 */
function newResume() {
  draftId.value = null;
  seriesId.value = null;
  error.value = "";
}

function resolveLogicalDisplayName(store) {
  let base = displayName.value.trim();
  if (!base) {
    base = nextDisplayName({
      studentNo: basic.value.学号,
      name: basic.value.姓名,
      store
    });
    displayName.value = base;
  }
  return base;
}

function getDraftRecord() {
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  return draftId.value ? (store.resumes || []).find((r) => r.id === draftId.value) : null;
}

async function persistPut(sid, resumeId, payload) {
  resumeStore.value = await resumeApi.putResume(sid, resumeId, payload);
}

async function onSetDefault(id, scope = "series") {
  if (hasStudentContext()) {
    try {
      resumeStore.value = await resumeApi.setDefaultResumeOnServer(getStudentId().trim(), id, scope);
      error.value = "";
    } catch (e) {
      error.value = e.message || "设置默认失败";
    }
    return;
  }
  setDefaultResume(id, scope);
  await refreshStore();
}

async function onDelete(id) {
  if (!confirm("确定删除该版本记录？")) return;
  if (hasStudentContext()) {
    try {
      resumeStore.value = await resumeApi.deleteResumeOnServer(getStudentId().trim(), id);
      if (draftId.value === id) resetDraft();
      error.value = "";
    } catch (e) {
      error.value = e.message || "删除失败";
    }
    return;
  }
  deleteResume(id);
  if (draftId.value === id) resetDraft();
  await refreshStore();
}

function buildExportJsonPayload(rec) {
  if (rec) {
    return {
      ...rec,
      exportedAt: Date.now()
    };
  }
  return {
    id: draftId.value || "(未保存)",
    templateId: selectedTemplateId.value,
    displayName: displayName.value || "(未命名)",
    content: buildContent(),
    exportedAt: Date.now()
  };
}

function resolveExportRecord(record) {
  if (record) return record;
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  const id = draftId.value;
  return id ? store.resumes.find((r) => r.id === id) || null : null;
}

async function exportResume(format = "json", record = null) {
  error.value = "";
  const rec = resolveExportRecord(record);
  const model = rec
    ? buildResumeDocumentModelFromRecord(rec, currentTemplate.value)
    : buildResumeDocumentModel({
        template: currentTemplate.value,
        basic: buildBasicForSave(toRaw(basic.value)),
        intent: {
          targetJobs: String(intent.value.targetJobs ?? "").trim(),
          targetCompanies: String(intent.value.targetCompanies ?? "").trim()
        },
        sections: serializeSections(toRaw(sections.value)),
        extraNotes: extraNotes.value.trim(),
        displayName: displayName.value.trim() || buildCurrentDisplayName(rec)
      });
  const jsonPayload = buildExportJsonPayload(rec);
  try {
    await exportResumeByFormat(format, model, jsonPayload);
    resumeApplyNotice.value =
      format === "json"
        ? "已导出 JSON 文件"
        : format === "pdf"
          ? "已导出 PDF 文件"
          : "已导出 Word 文件";
  } catch (e) {
    error.value = e?.message || "导出失败";
  }
}

const previewText = computed(() =>
  formatResumePreviewText({
    template: currentTemplate.value,
    basic: basic.value,
    intent: intent.value,
    sections: sections.value,
    extraNotes: extraNotes.value
  })
);

const leftDraftContent = computed(() => buildContent());

function updateSectionItems(key, items) {
  sections.value = { ...sections.value, [key]: items };
}

/** 从岗位卡片带入的优化素材（router.push state） */
function consumeRouterResumeAiContextState() {
  const raw = history.state?.resumeAiContext;
  if (!raw || typeof raw !== "object" || !raw.kind || !raw.refId) return;
  openAiPanel();
  dispatchResumeAiContext(raw);
  resumeApplyNotice.value = "已将推荐岗位加入优化素材篮";
  try {
    const next = { ...(history.state || {}) };
    delete next.resumeAiContext;
    history.replaceState(next, "");
  } catch (_) {
    /* ignore */
  }
}
/** 从对话页 router.push state 带入的 resume_render（跳转后再合并，避免被默认简历覆盖） */
function consumeRouterResumeRenderState() {
  const raw = history.state?.resumeRender;
  if (!raw || typeof raw !== "object") return;
  applyResumeRenderPayload(raw);
  try {
    const next = { ...(history.state || {}) };
    delete next.resumeRender;
    history.replaceState(next, "");
  } catch (_) {
    /* ignore */
  }
}

let unsubscribeResumeRender = () => {};

onMounted(async () => {
  window.scrollTo(0, 0);
  await Promise.all([loadStudent(), refreshStore()]);
  const store = resumeStore.value;
  const defId = store.defaultResumeId;
  if (defId && !draftId.value) {
    const globalRec = store.resumes?.find((r) => r.id === defId);
    if (globalRec) {
      const ser = globalRec.seriesId || globalRec.id;
      const versions = (store.resumes || []).filter((r) => (r.seriesId || r.id) === ser);
      const target = pickSeriesDefaultVersion(versions, defId) || globalRec;
      await loadRecord(target.id);
    }
  }
  // 须在默认简历 loadRecord 之后再订阅/消费，否则聊天页 pending 会被覆盖
  unsubscribeResumeRender = subscribeResumeRender((payload) => {
    applyResumeRenderPayload(payload);
  });
  consumeRouterResumeRenderState();
  await nextTick();
  consumeRouterResumeAiContextState();
});

onBeforeUnmount(() => {
  unsubscribeResumeRender();
  if (noticeTimer) clearTimeout(noticeTimer);
});
</script>
<template>
  <ResumeStudioLayout
    :embed="isEmbed"
    :drawer-open="showRightRail"
    :drawer-title="drawerTitle"
    :templates-open="templatesPanelOpen"
    top-bar-title="我的简历"
    :top-bar-subtitle="pageSubtitle"
    :student-name="studentDisplayName"
    @close-drawer="closeRightPanel"
    @update:templates-open="templatesPanelOpen = $event"
  >
    <template #alerts>
      <p v-if="resumeApplyNotice" class="rs-alert rs-alert--success" role="status">{{ resumeApplyNotice }}</p>
      <p v-if="error" class="rs-alert rs-alert--error">{{ error }}</p>
      <p v-if="loadingStudent" class="rs-alert rs-alert--muted">正在加载学生信息…</p>
      <p v-if="loadingRecord" class="rs-alert rs-alert--muted">正在从服务端加载简历…</p>
    </template>

    <template #templates>
      <ResumeTemplateSidebar
        v-model="selectedTemplateId"
        :collapsed="!templatesPanelOpen"
        @update:collapsed="templatesPanelOpen = !$event"
        @upload="handleTemplateUpload"
      />
    </template>

    <template #editor-prefix>
      <ResumeTemplateStrip v-if="isEmbed" v-model="selectedTemplateId" />
    </template>

    <template #editor>
      <ResumeEditorSheet
        :editor-title="editorTitle"
        :hero-name="heroName"
        :hero-subtitle="heroSubtitle"
        :phone="heroPhone"
        :email="heroEmail"
        :avatar-url="avatarUrl"
        :version-open="activeRightPanel === 'version'"
        :ai-open="activeRightPanel === 'ai'"
        :saving="saving"
        :basic="basic"
        :intent="intent"
        :sections="sections"
        :section-edit-mode="sectionEditMode"
        :current-template="currentTemplate"
        :basic-info-keys="BASIC_INFO_KEYS"
        :contact-info-keys="CONTACT_INFO_KEYS"
        @change-avatar="handleAvatarChange"
        @version-preview="toggleVersionPanel"
        @export="exportResume"
        @ai-optimize="toggleAiPanel"
        @toggle-edit-section="toggleEditSection"
        @update:items="updateSectionItems"
      />
    </template>

    <template #drawer>
      <div v-if="activeRightPanel === 'version'" class="rs-rail-card">
        <ResumeVersionPreviewPanel
          :style="{ '--vpp-accent': currentTemplate.accent }"
          :active-series="activeSeriesGroup"
          :resume-groups="resumeGroups"
          :series-id="seriesId"
          :draft-id="draftId"
          :saving="saving"
          :can-save-in-place="canSaveInPlace"
          :accent="currentTemplate.accent"
          @load-version="loadRecord"
          @delete-version="onDelete"
          @select-group="selectResumeGroup"
          @save-as-copy="saveAsNewResume"
          @save-draft="saveDraft"
          @export="({ format, record }) => exportResume(format, record)"
        />
      </div>
      <div v-else-if="activeRightPanel === 'ai'" class="rs-rail-card rs-rail-card--ai">
        <ResumeAiOptimizeRail
          embedded
          :student-id="getStudentId()"
          :left-draft-preview="previewText"
          :left-draft-content="leftDraftContent"
          :template-id="selectedTemplateId"
          :display-name="displayName"
          @resume-render="applyResumeRenderPayload"
        />
      </div>
    </template>
  </ResumeStudioLayout>

  <ResumeCopyModal
    :open="copyModalOpen"
    :group="copyModalGroup"
    :draft-id="draftId"
    @close="closeCopyModal"
    @load="syncCopyFromModal"
    @set-default="setDefaultFromModal"
    @delete="deleteCopyFromModal"
    @delete-series="deleteEntireSeriesFromModal"
  />
</template>
