<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRaw, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet } from "../api/client";
import ResumeCopyModal from "../components/resume/ResumeCopyModal.vue";
import ResumeSectionBlocks from "../components/resume/ResumeSectionBlocks.vue";
import ResumeVersionRail from "../components/resume/ResumeVersionRail.vue";
import ResumeAiOptimizeRail from "../components/resume/ResumeAiOptimizeRail.vue";
import ResumeStudioFloatWindow from "../components/resume/ResumeStudioFloatWindow.vue";
import { buildBasicForSave, parseResumeContent } from "../modules/resume/content";
import { emptySectionsForTemplate, prefillBasicFromPortrait } from "../modules/resume/prefill";
import {
  normalizeSectionItems,
  sectionAllowsMultiple,
  serializeSections
} from "../modules/resume/sectionsModel";
import {
  RESUME_TEMPLATES,
  getSectionField,
  getTemplateById,
  mapSectionsOnTemplateChange
} from "../modules/resume/templates";
import {
  appendTimeCopySuffix,
  deleteResume,
  loadStore,
  newResumeId,
  nextDisplayName,
  pickSeriesDefaultVersion,
  setDefaultResume,
  stripTimeCopySuffix,
  updateResumeInPlace,
  upsertResumeNewVersion
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
import { mergeResumeRenderIntoEditor } from "../modules/resume/applyRenderPayload";
import { formatResumePreviewText } from "../modules/resume/previewText";

const route = useRoute();
const isEmbed = computed(() => route.query._embed === "1");

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
const templateScrollerRef = ref(null);
/** 一屏展示的模版数量 */
const TEMPLATES_PER_VIEW = 3;
const templatePageIndex = ref(0);

const templatePages = computed(() => {
  const pages = [];
  for (let i = 0; i < RESUME_TEMPLATES.length; i += TEMPLATES_PER_VIEW) {
    pages.push(RESUME_TEMPLATES.slice(i, i + TEMPLATES_PER_VIEW));
  }
  return pages;
});

const templatePageCount = computed(() => templatePages.value.length);

const canScrollTemplatePrev = computed(() => templatePageIndex.value > 0);
const canScrollTemplateNext = computed(
  () => templatePageIndex.value < templatePageCount.value - 1
);

const versionFullscreen = ref(false);
const aiFullscreen = ref(false);

function toggleVersionPanel() {
  if (studioRailVisible.value) {
    setResumeStudioRailVisible(false);
    versionFullscreen.value = false;
  } else {
    setResumeStudioRailVisible(true);
  }
}

function toggleAiPanel() {
  if (aiRailVisible.value) {
    setResumeAiRailVisible(false);
    aiFullscreen.value = false;
  } else {
    setResumeAiRailVisible(true);
  }
}

function openVersionPanel() {
  setResumeStudioRailVisible(true);
}

function openAiPanel() {
  setResumeAiRailVisible(true);
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
    return "将创建新简历线及首条副本，并设为该线的「本简历默认」。";
  }
  return "「保存当前副本」覆盖本条，不产生新历史。「另存为新副本」保留本条并新增带时间戳记录。";
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

const headerSubtitle = computed(() => {
  const parts = [];
  if (draftId.value && activeSeriesGroup.value) {
    parts.push(`编辑：${stripTimeCopySuffix(displayName.value || activeSeriesGroup.value.label)}`);
  } else if (seriesId.value) {
    parts.push("新简历线（未保存）");
  } else {
    parts.push("新草稿");
  }
  if (globalDefaultRecord.value) {
    parts.push(`对话默认：${stripTimeCopySuffix(globalDefaultRecord.value.displayName || "")}`);
  }
  return parts.join(" · ");
});

watch(selectedTemplateId, (tid, prevTid) => {
  if (!prevTid || prevTid === tid) return;
  const fromTpl = getTemplateById(prevTid);
  const toTpl = getTemplateById(tid);
  sections.value = mapSectionsOnTemplateChange({ ...sections.value }, fromTpl, toTpl);
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
    studentPortrait.value = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
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

/** 原地保存时保留副本名上的时间戳后缀，并同步右侧逻辑名称。 */
function buildInPlaceDisplayName(existing) {
  const full = String(existing?.displayName || "").trim();
  const logical = displayName.value.trim() || stripTimeCopySuffix(full) || "简历";
  const m = full.match(/^(.*)_(\d{14})$/);
  if (m) {
    return `${logical}_${m[2]}`;
  }
  return full || appendTimeCopySuffix(logical);
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

/** 原地保存当前副本 */
async function saveDraft() {
  const sid = getStudentId().trim();
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  if (!draftId.value) {
    await saveAsNewVersion();
    return;
  }
  const existing = getDraftRecord();
  if (!existing) {
    await saveAsNewVersion();
    return;
  }
  const ser = seriesId.value || existing.seriesId || existing.id;
  seriesId.value = ser;
  const payload = {
    seriesId: ser,
    templateId: selectedTemplateId.value,
    displayName: buildInPlaceDisplayName(existing),
    content: buildContent(),
    setSeriesDefault: true,
    setGlobalDefault: setAsGlobalDefault.value
  };
  saving.value = true;
  try {
    if (sid) {
      await persistPut(sid, draftId.value, payload);
      await loadRecord(draftId.value);
    } else {
      resumeStore.value = updateResumeInPlace(
        {
          ...existing,
          ...payload,
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

/** 另存为带时间戳的新副本 */
async function saveAsNewVersion() {
  const sid = getStudentId().trim();
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  const ser = seriesId.value || newResumeId();
  seriesId.value = ser;
  const base = resolveLogicalDisplayName(store);
  const versionName = appendTimeCopySuffix(base);
  const newId = newResumeId();
  const payload = {
    seriesId: ser,
    templateId: selectedTemplateId.value,
    displayName: versionName,
    content: buildContent(),
    createdAt: Date.now(),
    setSeriesDefault: true,
    setGlobalDefault: setAsGlobalDefault.value
  };
  saving.value = true;
  try {
    if (sid) {
      await persistPut(sid, newId, payload);
      draftId.value = newId;
      await loadRecord(newId);
    } else {
      resumeStore.value = upsertResumeNewVersion(
        {
          id: newId,
          templateId: selectedTemplateId.value,
          displayName: versionName,
          content: buildContent(),
          createdAt: Date.now()
        },
        ser,
        { setGlobalDefault: setAsGlobalDefault.value }
      );
      draftId.value = newId;
      await loadRecord(newId);
    }
    error.value = "";
  } catch (e) {
    error.value = e.message || "另存为副本失败";
  } finally {
    saving.value = false;
  }
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
  if (!confirm("确定删除该副本？（同一份简历下其他副本仍保留；多份简历互不影响）")) return;
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

function exportJson() {
  const store = hasStudentContext() ? resumeStore.value : loadStore();
  const id = draftId.value;
  const rec = id ? store.resumes.find((r) => r.id === id) : null;
  const payload = rec || {
    id: draftId.value || "(未保存)",
    templateId: selectedTemplateId.value,
    displayName: displayName.value || "(未命名)",
    content: buildContent(),
    exportedAt: Date.now()
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${(displayName.value || "简历").replace(/[/\\?%*:|"<>]/g, "-")}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
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

function sectionField(key) {
  return getSectionField(currentTemplate.value, key);
}

function sectionEntryLabel(key) {
  if (key.includes("经历")) return "条经历";
  if (key.includes("项目") || key.includes("作品")) return "条记录";
  if (key.includes("论文") || key.includes("专利")) return "条";
  if (key.includes("竞赛") || key.includes("开源")) return "条";
  if (key.includes("获奖")) return "条";
  return "条";
}

function updateSectionItems(key, items) {
  sections.value = { ...sections.value, [key]: items };
}

function scrollToTemplatePage(pageIndex) {
  const el = templateScrollerRef.value;
  if (!el) return;
  const maxPage = Math.max(0, templatePageCount.value - 1);
  const next = Math.max(0, Math.min(maxPage, pageIndex));
  templatePageIndex.value = next;
  el.scrollTo({ left: next * el.clientWidth, behavior: "smooth" });
}

function scrollTemplates(direction) {
  scrollToTemplatePage(templatePageIndex.value + direction);
}

function onTemplateScroll() {
  const el = templateScrollerRef.value;
  if (!el?.clientWidth) return;
  templatePageIndex.value = Math.round(el.scrollLeft / el.clientWidth);
}

function scrollActiveTemplateIntoView() {
  const idx = RESUME_TEMPLATES.findIndex((t) => t.id === selectedTemplateId.value);
  if (idx < 0) return;
  scrollToTemplatePage(Math.floor(idx / TEMPLATES_PER_VIEW));
}

watch(selectedTemplateId, () => {
  nextTick(scrollActiveTemplateIntoView);
});

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
  nextTick(scrollActiveTemplateIntoView);
});

onBeforeUnmount(() => {
  unsubscribeResumeRender();
});
</script>
<template>
  <div class="page resume-studio" :class="{ 'resume-studio--embed': isEmbed }">
    <div class="studio-shell">
    <p v-if="resumeApplyNotice" class="resume-apply-banner" role="status">{{ resumeApplyNotice }}</p>
    <header class="studio-header">
      <div class="studio-header-inner">
        <div class="studio-header-brand">
          <span v-if="!isEmbed" class="studio-header-badge">Resume Studio</span>
          <div class="studio-header-heading">
            <h1>创建简历</h1>
            <p v-if="headerSubtitle" class="studio-header-sub">{{ headerSubtitle }}</p>
          </div>
        </div>
        <div class="studio-header-toolbar" role="toolbar" aria-label="简历工具窗口">
          <button
            type="button"
            class="studio-tool-btn studio-tool-btn--clear"
            title="清空当前表单内容"
            @click="clearFormData"
          >
            <span class="studio-tool-icon" aria-hidden="true">⌫</span>
            <span class="studio-tool-label">清空表单</span>
          </button>
          <button
            type="button"
            class="studio-tool-btn studio-tool-btn--version"
            :class="{ 'studio-tool-btn--open': studioRailVisible }"
            :aria-pressed="studioRailVisible"
            title="版本、保存与预览"
            @click="toggleVersionPanel"
          >
            <span class="studio-tool-icon" aria-hidden="true">◇</span>
            <span class="studio-tool-label">{{ studioRailVisible ? "关闭版本" : "版本与预览" }}</span>
          </button>
          <button
            type="button"
            class="studio-tool-btn studio-tool-btn--ai"
            :class="{ 'studio-tool-btn--open': aiRailVisible }"
            :aria-pressed="aiRailVisible"
            title="AI 简历优化"
            @click="toggleAiPanel"
          >
            <span class="studio-tool-icon" aria-hidden="true">✦</span>
            <span class="studio-tool-label">{{ aiRailVisible ? "关闭 AI" : "AI 优化" }}</span>
          </button>
        </div>
      </div>
    </header>

    <p v-if="error" class="error studio-error">{{ error }}</p>
    <p v-if="loadingStudent" class="muted studio-loading">正在加载学生信息…</p>
    <p v-if="loadingRecord" class="muted studio-loading">正在从服务端加载简历…</p>

    <div class="studio-body">
    <div class="studio-layout studio-layout--single">
      <main class="studio-main">
        <section class="panel">
          <h2 class="section-title">选择模版</h2>
          <p class="muted small template-intro">
            一屏展示 <strong>3</strong> 种模版，左右滑动或点箭头切换；共 {{ RESUME_TEMPLATES.length }} 种。当前选中：{{ currentTemplate.name }}
          </p>
          <div class="template-picker">
            <button
              type="button"
              class="template-nav"
              aria-label="上一组模版"
              :disabled="!canScrollTemplatePrev"
              @click="scrollTemplates(-1)"
            >
              ‹
            </button>
            <div
              ref="templateScrollerRef"
              class="template-scroll"
              role="listbox"
              aria-label="简历模版列表"
              @scroll.passive="onTemplateScroll"
            >
              <div
                v-for="(page, pi) in templatePages"
                :key="page[0]?.id || pi"
                class="template-page"
              >
                <label
                  v-for="tpl in page"
                  :key="tpl.id"
                  class="template-card"
                  :class="{ active: selectedTemplateId === tpl.id }"
                  :style="{ '--tpl-accent': tpl.accent }"
                  role="option"
                  :aria-selected="selectedTemplateId === tpl.id"
                >
                  <input v-model="selectedTemplateId" type="radio" name="tpl" :value="tpl.id" class="sr-only" />
                  <div class="template-card-head">
                    <strong>{{ tpl.name }}</strong>
                    <span class="template-badge">{{ tpl.badge }}</span>
                  </div>
                  <p class="template-desc">{{ tpl.description }}</p>
                  <ul class="template-highlights">
                    <li v-for="h in tpl.highlights" :key="h">{{ h }}</li>
                  </ul>
                </label>
              </div>
            </div>
            <button
              type="button"
              class="template-nav"
              aria-label="下一组模版"
              :disabled="!canScrollTemplateNext"
              @click="scrollTemplates(1)"
            >
              ›
            </button>
          </div>
          <div class="template-page-dots" role="tablist" aria-label="模版分页">
            <button
              v-for="(_, pi) in templatePages"
              :key="pi"
              type="button"
              class="template-dot"
              :class="{ active: templatePageIndex === pi }"
              :aria-label="`第 ${pi + 1} 组模版`"
              :aria-selected="templatePageIndex === pi"
              @click="scrollToTemplatePage(pi)"
            />
          </div>
        </section>

        <section class="panel panel-compact">
          <h2 class="section-title">基本信息</h2>
          <p class="muted small">可与学生画像预填对齐。</p>
          <div class="form-grid form-grid-basic">
            <label v-for="(_, key) in basic" :key="key" class="field">
              <span>{{ key }}</span>
              <input v-model="basic[key]" />
            </label>
          </div>
        </section>

        <section v-if="currentTemplate.intentMode === 'full'" class="panel panel-compact">
          <h2 class="section-title">求职意向</h2>
          <p class="muted small">标准/技术模版单独列出意向；简洁模版请写在第 4 步「求职意向说明」。</p>
          <div class="form-grid two-col">
            <label class="field field-wide">
              <span>意向岗位</span>
              <textarea v-model="intent.targetJobs" rows="3" placeholder="例如：前端开发、杭州、校招" />
            </label>
            <label class="field field-wide">
              <span>意向企业</span>
              <textarea v-model="intent.targetCompanies" rows="3" placeholder="例如：某行业头部、国企研究院等" />
            </label>
          </div>
        </section>

        <section class="panel panel--template-body">
          <div
            class="template-active-banner"
            :style="{ borderColor: currentTemplate.accent, background: `${currentTemplate.accent}12` }"
          >
            <span class="template-active-badge" :style="{ background: currentTemplate.accent }">{{ currentTemplate.badge }}</span>
            <span>当前模版：<strong>{{ currentTemplate.name }}</strong> — {{ currentTemplate.sectionKeys.length }} 个正文块</span>
          </div>
          <h2 class="section-title">简历正文</h2>
          <p class="muted small section-multi-hint">
            经历/项目类模块可添加多条；每条可填小标题与正文，预览自动编号。
          </p>
          <ResumeSectionBlocks
            v-for="key in currentTemplate.sectionKeys"
            :key="key"
            :section-key="key"
            :items="sections[key] || []"
            :hint="sectionField(key).hint"
            :placeholder="sectionField(key).placeholder"
            :rows="sectionField(key).rows"
            :allow-multiple="sectionAllowsMultiple(currentTemplate, key)"
            :entry-label="sectionEntryLabel(key)"
            :accent="currentTemplate.accent"
            @update:items="updateSectionItems(key, $event)"
          />
        </section>

<!--        <section class="panel panel-compact">-->
<!--          <h2 class="section-title">补充说明</h2>-->
<!--          <label class="field field-wide">-->
<!--            <span>其他希望写入简历或生成时参考的说明</span>-->
<!--            <textarea v-model="extraNotes" rows="4" placeholder="荣誉、学生工作、个人特点等可写在此处" />-->
<!--          </label>-->
<!--        </section>-->

      </main>
    </div>
    </div>
    </div>

    <ResumeStudioFloatWindow
      :open="studioRailVisible"
      title="版本 · 保存 · 预览"
      preset="version"
      v-model:fullscreen="versionFullscreen"
      @close="setResumeStudioRailVisible(false)"
    >
      <div class="studio-float-inner">
          <ResumeVersionRail
            :resume-groups="resumeGroups"
            :series-id="seriesId"
            :draft-id="draftId"
            :display-name="displayName"
            :set-as-global-default="setAsGlobalDefault"
            :saving="saving"
            :can-save-in-place="canSaveInPlace"
            :save-hint="saveHint"
            :has-student-context="hasStudentContext()"
            :student-id="getStudentId()"
            :global-default-id="globalDefaultId"
            :current-draft="currentDraftRecord"
            :active-series="activeSeriesGroup"
            :global-default-record="globalDefaultRecord"
            :accent="currentTemplate.accent"
            @update:display-name="displayName = $event"
            @update:set-as-global-default="setAsGlobalDefault = $event"
            @save-draft="saveDraft"
            @save-as-copy="saveAsNewVersion"
            @new-series="newResume"
            @export-json="exportJson"
            @select-group="selectResumeGroup"
            @load-version="loadRecord"
            @set-default="handleSetDefault"
            @delete-version="onDelete"
            @open-all-copies="openCopyModal"
          />
          <section class="panel panel-preview studio-float-preview">
            <h3 class="rail-title">实时预览</h3>
            <pre
              class="preview preview-rail"
              :class="`preview--${currentTemplate.id}`"
              :style="{ borderLeftColor: currentTemplate.accent }"
            >{{ previewText || "（填写后在此预览）" }}</pre>
          </section>
      </div>
    </ResumeStudioFloatWindow>

    <ResumeStudioFloatWindow
      :open="aiRailVisible"
      title="AI 简历优化"
      preset="ai"
      v-model:fullscreen="aiFullscreen"
      @close="setResumeAiRailVisible(false)"
    >
      <ResumeAiOptimizeRail
        embedded
        :student-id="getStudentId()"
        :left-draft-preview="previewText"
        :left-draft-content="leftDraftContent"
        :template-id="selectedTemplateId"
        :display-name="displayName"
        @resume-render="applyResumeRenderPayload"
      />
    </ResumeStudioFloatWindow>

    <button
      v-if="!studioRailVisible"
      type="button"
      class="studio-rail-fab studio-rail-fab--version"
      title="打开版本与预览窗口"
      @click="openVersionPanel"
    >
      版本栏
    </button>
    <button
      v-if="!aiRailVisible"
      type="button"
      class="studio-rail-fab studio-rail-fab--ai"
      title="打开 AI 简历优化窗口"
      @click="openAiPanel"
    >
      AI 优化
    </button>

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
  </div>
</template>
<style scoped>
.page {
  min-height: 100vh;
  position: relative;
}
.resume-apply-banner {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  font-size: 0.88rem;
}
.resume-studio {
  padding-bottom: 48px;
  background: linear-gradient(180deg, #f1f5f9 0%, #f8fafc 140px, #f8fafc 100%);
}
.studio-shell {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
.studio-body {
  min-width: 0;
}
.studio-header {
  padding: 18px 20px 12px;
}
.studio-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px 20px;
  flex-wrap: wrap;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #e8ecf4;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 48%, #f5f3ff 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 10px 28px rgba(15, 23, 42, 0.06);
}
.studio-header-brand {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
  flex: 1;
}
.studio-header-badge {
  flex-shrink: 0;
  margin-top: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #4338ca;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
}
.studio-header-heading {
  min-width: 0;
}
.studio-header-heading h1 {
  margin: 0;
  font-size: clamp(1.25rem, 2.6vw, 1.65rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #0f172a;
  line-height: 1.25;
}
.studio-header-sub {
  margin: 6px 0 0;
  font-size: 0.8rem;
  color: #64748b;
  line-height: 1.45;
}
.studio-header-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 4px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid #e2e8f0;
}
.studio-tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.studio-tool-btn:hover {
  background: #fff;
  border-color: #e2e8f0;
  color: #1e293b;
}
.studio-tool-icon {
  font-size: 0.9rem;
  line-height: 1;
  opacity: 0.85;
}
.studio-tool-btn--clear:hover {
  color: #b45309;
  background: #fffbeb;
  border-color: #fcd34d;
}
.studio-tool-btn--version.studio-tool-btn--open,
.studio-tool-btn--version:hover {
  color: #4338ca;
}
.studio-tool-btn--version.studio-tool-btn--open {
  background: #eef2ff;
  border-color: #c7d2fe;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
}
.studio-tool-btn--ai.studio-tool-btn--open,
.studio-tool-btn--ai:hover {
  color: #7c3aed;
}
.studio-tool-btn--ai.studio-tool-btn--open {
  background: #f3e8ff;
  border-color: #d8b4fe;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.12);
}
.studio-tool-btn--ai .studio-tool-icon {
  color: #a855f7;
}
.studio-error,
.studio-loading {
  padding: 0 20px 8px;
}
.studio-layout {
  padding: 0 20px 20px;
}
.studio-layout--single {
  display: block;
}
.studio-rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  margin: -4px 0 2px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f6;
}
.studio-rail-head-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #64748b;
}
.studio-rail-hide-btn {
  flex-shrink: 0;
  padding: 4px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.studio-rail-hide-btn:hover {
  border-color: #c7d2fe;
  color: var(--primary-color);
}
.studio-float-inner {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.studio-float-preview {
  margin: 0;
}
.studio-float-preview .preview-rail {
  max-height: min(280px, 40vh);
}
.studio-rail-fab {
  position: fixed;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 12480;
  padding: 10px 14px;
  border-radius: 12px 0 0 12px;
  border: 1px solid #e2e8f0;
  border-right: none;
  background: #fff;
  color: var(--primary-color);
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: -4px 0 20px rgba(15, 23, 42, 0.08);
  writing-mode: vertical-rl;
  letter-spacing: 0.08em;
}
.studio-rail-fab:hover {
  background: #f5f3ff;
  border-color: #c7d2fe;
}
.studio-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.studio-rail {
  min-width: 0;
}
.rail-sticky {
  position: sticky;
  top: 72px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.rail-title {
  margin: 0 0 10px;
  font-size: 0.95rem;
}
.panel-compact {
  padding: 14px 16px;
}
.panel-compact .section-title {
  margin-bottom: 8px;
}
.panel-preview {
  padding: 14px 16px;
}
.preview-rail {
  max-height: min(420px, 50vh);
  margin: 0;
  font-size: 0.75rem;
}
.form-grid-basic {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.section-multi-hint {
  margin: -4px 0 12px;
}
.panel-meta .btn-row-wrap {
  margin: 10px 0;
}
.hero {
  padding: 86px 20px 40px;
  text-align: center;
  background: radial-gradient(circle at top right, #eef2ff, transparent),
    radial-gradient(circle at top left, #f5f3ff, transparent);
}
.badge {
  display: inline-block;
  padding: 5px 14px;
  background: #e0e7ff;
  color: var(--primary-color);
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 12px;
}
.hero h1 {
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  margin: 0 0 8px;
}
.hero p {
  color: var(--text-muted);
  max-width: 560px;
  margin: 0 auto;
  font-size: 0.95rem;
}
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 80px;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
}
.main-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel {
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  padding: 18px;
}
.section-title {
  font-size: 1.05rem;
  margin: 0 0 12px;
}
.muted {
  color: var(--text-muted);
}
.small {
  font-size: 0.82rem;
}
.error {
  color: var(--danger);
  font-weight: 600;
  font-size: 0.9rem;
}
.template-picker {
  display: flex;
  align-items: stretch;
  gap: 8px;
}
.template-nav {
  flex-shrink: 0;
  width: 36px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  color: #475569;
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition: var(--transition);
  align-self: center;
  min-height: 120px;
}
.template-nav:hover {
  border-color: #c7d2fe;
  background: #f8fafc;
  color: var(--primary-color);
}
.template-scroll {
  display: flex;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  padding: 4px 0 8px;
  scrollbar-width: none;
}
.template-scroll::-webkit-scrollbar {
  display: none;
}
.template-page {
  flex: 0 0 100%;
  display: flex;
  gap: 12px;
  scroll-snap-align: start;
  box-sizing: border-box;
}
.template-page-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 10px;
}
.template-dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: #d1d5db;
  cursor: pointer;
  transition: var(--transition);
}
.template-dot.active {
  width: 22px;
  background: var(--primary-color);
}
.template-nav:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.template-card {
  flex: 1 1 0;
  min-width: 0;
  border: 2px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px 14px;
  cursor: pointer;
  transition: var(--transition);
  display: block;
}
.template-card:hover {
  border-color: #c7d2fe;
}
.template-intro {
  margin: 0 0 12px;
}
.template-card.active {
  border-color: var(--tpl-accent, var(--primary-color));
  background: linear-gradient(180deg, #fff, color-mix(in srgb, var(--tpl-accent, #6366f1) 8%, #fff));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--tpl-accent, #6366f1) 35%, transparent);
}
.template-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.template-card-head strong {
  font-size: 0.95rem;
}
.template-badge {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tpl-accent, #6366f1) 18%, #fff);
  color: var(--tpl-accent, #4338ca);
}
.template-desc {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.45;
}
.template-highlights {
  margin: 0 0 10px;
  padding-left: 1.1em;
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.5;
}
.template-outline {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.outline-chip {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
}
.outline-chip--section {
  background: color-mix(in srgb, var(--tpl-accent, #6366f1) 12%, #f8fafc);
  color: #334155;
  border: 1px solid color-mix(in srgb, var(--tpl-accent, #6366f1) 25%, #e2e8f0);
}
.template-active-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid;
  margin-bottom: 14px;
  font-size: 0.84rem;
  color: #334155;
}
.template-active-badge {
  color: #fff;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.section-label {
  font-weight: 600;
  color: #1e293b;
}
.section-hint {
  margin: 0 0 6px;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.4;
}
.preview {
  border-left: 4px solid var(--primary-color);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.form-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.form-grid.two-col {
  grid-template-columns: 1fr;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field span {
  font-size: 0.78rem;
  color: var(--text-muted);
}
.field input,
.field textarea {
  width: 100%;
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 0.88rem;
  font-family: inherit;
}
.field textarea {
  resize: vertical;
  min-height: 72px;
}
.field-wide {
  grid-column: 1 / -1;
}
.block-field + .block-field {
  margin-top: 12px;
}
.preview {
  margin: 0;
  padding: 14px;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 0.8rem;
  line-height: 1.55;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
}
.actions-panel .row {
  margin-bottom: 10px;
}
.field-inline {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.field-inline span {
  font-size: 0.78rem;
  color: var(--text-muted);
}
.field-inline input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #dbe1ea;
  font-size: 0.9rem;
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.btn {
  padding: 10px 16px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
}
.btn.primary {
  background: var(--primary-color);
  color: #fff;
}
.btn.ghost {
  background: #fff;
  color: var(--text-main);
  border: 1px solid #d1d5db;
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sidebar-hint {
  margin-bottom: 10px;
}
.sid-code {
  font-size: 0.78rem;
  word-break: break-all;
}
.resume-summary-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.resume-summary-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fcfcff;
}
.resume-summary-card.active {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.22);
}
.resume-summary-body {
  min-width: 0;
  flex: 1;
}
.resume-summary-title {
  font-weight: 700;
  font-size: 0.88rem;
  color: #1e293b;
}
.resume-summary-meta {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 10px;
  font-size: 0.82rem;
  color: var(--text-muted);
  cursor: pointer;
}
.checkbox-row input {
  margin-top: 3px;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.mini-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.mini {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
}
.mini.danger {
  color: var(--danger);
  border-color: #fecaca;
}
code {
  font-size: 0.78rem;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 6px;
}
@media (max-width: 980px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
  .rail-sticky {
    position: static;
  }
  .preview-rail {
    max-height: 280px;
  }
  .studio-header {
    padding-top: 14px;
  }
  .resume-studio--embed .studio-header {
    padding-top: 0;
  }
  .studio-header-inner {
    flex-direction: column;
    align-items: stretch;
  }
  .studio-header-toolbar {
    width: 100%;
    justify-content: stretch;
  }
  .studio-tool-btn {
    flex: 1;
    justify-content: center;
  }
  .studio-tool-label {
    font-size: 0.78rem;
  }
  .container {
    grid-template-columns: 1fr;
  }
  .form-grid,
  .form-grid-basic {
    grid-template-columns: 1fr;
  }
  .template-nav {
    width: 32px;
    min-height: 100px;
  }
}

.studio-rail-fab--version {
  top: 46%;
}
.studio-rail-fab--ai {
  top: 58%;
  background: linear-gradient(180deg, #faf5ff, #fff);
  color: #7c3aed;
  border-color: #e9d5ff;
}
.studio-rail-fab--ai:hover {
  background: #f3e8ff;
  border-color: #c084fc;
}

/* 导航浮层 iframe 内嵌：填满视口、紧凑顶栏、内容区独立滚动 */
.resume-studio--embed {
  min-height: 100dvh;
  height: 100dvh;
  padding-bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f1f5f9;
}
.resume-studio--embed .studio-shell {
  flex: 1;
  min-height: 0;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
}
.resume-studio--embed .studio-header {
  flex-shrink: 0;
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 20;
}
.resume-studio--embed .studio-header-inner {
  border-radius: 0;
  border: none;
  border-bottom: 1px solid #e8ecf4;
  padding: 10px 14px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}
.resume-studio--embed .studio-header-heading h1 {
  font-size: 1.05rem;
}
.resume-studio--embed .studio-header-sub {
  font-size: 0.72rem;
  margin-top: 2px;
}
.resume-studio--embed .studio-header-toolbar {
  padding: 2px;
  background: #f8fafc;
}
.resume-studio--embed .studio-tool-btn {
  padding: 6px 10px;
  font-size: 0.76rem;
}
.resume-studio--embed .studio-error,
.resume-studio--embed .studio-loading {
  flex-shrink: 0;
  padding: 0 14px 6px;
}
.resume-studio--embed .studio-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}
.resume-studio--embed .studio-layout {
  padding: 12px 14px 20px;
}
.resume-studio--embed .panel {
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
}
.resume-studio--embed .studio-rail-fab {
  position: absolute;
  top: auto;
  transform: none;
  writing-mode: horizontal-tb;
  letter-spacing: 0;
  border-right: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px 12px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.1);
}
.resume-studio--embed .studio-rail-fab--version {
  right: 96px;
  bottom: 14px;
}
.resume-studio--embed .studio-rail-fab--ai {
  right: 14px;
  bottom: 14px;
}
</style>

<style>
/* 浮层 iframe 内：根节点占满高度，避免双层滚动与顶栏留白 */
html:has(.resume-studio--embed),
body:has(.resume-studio--embed) {
  height: 100%;
  overflow: hidden;
}
body:has(.resume-studio--embed) #app {
  height: 100%;
}
</style>
