<script setup>
/**
 * 创建简历页 · AI 简历优化侧栏：素材采集 + ROLE004 流式生成，自动填入左侧编辑器。
 * 1. OCR 解析上传简历  2. 收藏岗位  3. 关注企业  4. 用户补充说明
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import OcrView from "../../views/OcrView.vue";
import { apiGet, apiPost, apiPostSse } from "../../api/client";
import { RESUME_AI_DRAG_MIME } from "../../constants/resumeAiDrag";
import { RESUME_OPTIMIZER_USERCODE } from "../../constants/resumeOptimizer";
import { dispatchResumeRender } from "../../composables/useResumeRenderBridge";
import { subscribeResumeAiContext } from "../../composables/useResumeAiContextBridge";
import { buildCompanyContextItem, buildJobContextItem } from "../../modules/resume/aiContext";
import { resumePreviewHasContent } from "../../modules/resume/previewText";

const INCLUDE_LEFT_FORM_KEY = "resume_ai_include_left_form";

const props = defineProps({
  studentId: { type: String, default: "" },
  /** 浮窗内嵌时隐藏自带标题栏 */
  embedded: { type: Boolean, default: false },
  /** 与版本栏「实时预览」一致的左侧表单纯文本 */
  leftDraftPreview: { type: String, default: "" },
  /** 左侧表单结构化 content（basic/intent/sections/extraNotes） */
  leftDraftContent: { type: Object, default: null },
  templateId: { type: String, default: "" },
  displayName: { type: String, default: "" }
});

const emit = defineEmits(["close", "resume-render"]);

const loading = ref(false);
const loadError = ref("");
const favoriteJobs = ref([]);
const followedCompanies = ref([]);

/** @type {import('vue').Ref<Array<{ id: string, kind: string, title: string, subtitle?: string, payload?: unknown }>>} */
const contextItems = ref([]);
const supplementalNotes = ref("");
const dropActive = ref(false);
const submitState = ref("idle"); // idle | submitting | done | error
const submitMessage = ref("");
let streamAbortController = null;
const previewVisible = ref(false);
const includeLeftForm = ref(
  typeof localStorage !== "undefined" && localStorage.getItem(INCLUDE_LEFT_FORM_KEY) === "1"
);
const sid = computed(() => (props.studentId || "").trim());
const guest = computed(() => !sid.value);

const leftDraftReady = computed(() => resumePreviewHasContent(props.leftDraftPreview));

const includeLeftFormEffective = computed(
  () => includeLeftForm.value && leftDraftReady.value
);

const favList = computed(() => favoriteJobs.value || []);
const folList = computed(() => followedCompanies.value || []);

const canSubmit = computed(() => {
  if (guest.value || submitState.value === "submitting") return false;
  const hasRail =
    contextItems.value.length > 0 || supplementalNotes.value.trim().length > 0;
  return hasRail || includeLeftFormEffective.value;
});

const contextSummary = computed(() => {
  const n = contextItems.value.length;
  const kinds = { draft: 0, ocr: 0, job: 0, company: 0 };
  for (const it of contextItems.value) {
    if (kinds[it.kind] != null) kinds[it.kind] += 1;
  }
  const parts = [];
  if (includeLeftFormEffective.value) parts.push("左侧表单");
  if (kinds.ocr) parts.push(`简历解析 ${kinds.ocr}`);
  if (kinds.job) parts.push(`岗位 ${kinds.job}`);
  if (kinds.company) parts.push(`企业 ${kinds.company}`);
  return n || includeLeftFormEffective.value
    ? parts.join(" · ")
    : "拖入岗位/企业，或完成 OCR 后加入素材";
});

function newItemId() {
  return `rai-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function removeItem(id) {
  contextItems.value = contextItems.value.filter((x) => x.id !== id);
}

function addContextItem(item) {
  const dup =
    item.kind === "ocr"
      ? false
      : contextItems.value.some((x) => x.kind === item.kind && x.refId === item.refId);
  if (dup) return;
  contextItems.value = [...contextItems.value, { id: newItemId(), ...item }];
}

function onOcrRecognized(payload) {
  const text = String(payload?.text || "").trim();
  if (!text) return;
  addContextItem({
    kind: "ocr",
    title: payload.fileName ? `简历：${payload.fileName}` : "简历 OCR 文本",
    subtitle: `共 ${payload.count || 0} 条识别结果`,
    refId: `ocr-${Date.now()}`,
    payload: { text, ...payload }
  });
}

function jobDragPayload(job) {
  return buildJobContextItem(job) || { kind: "job", refId: "", title: "", payload: job };
}

function companyDragPayload(company) {
  return buildCompanyContextItem(company) || { kind: "company", refId: "", title: "", payload: company };
}

function onDragStart(ev, payload) {
  ev.dataTransfer.setData(RESUME_AI_DRAG_MIME, JSON.stringify(payload));
  ev.dataTransfer.effectAllowed = "copy";
}

function onDropZoneDragOver(ev) {
  if (ev.dataTransfer?.types?.includes(RESUME_AI_DRAG_MIME)) {
    ev.preventDefault();
    dropActive.value = true;
    ev.dataTransfer.dropEffect = "copy";
  }
}

function onDropZoneDragLeave() {
  dropActive.value = false;
}

function onDropZoneDrop(ev) {
  ev.preventDefault();
  dropActive.value = false;
  const raw = ev.dataTransfer?.getData(RESUME_AI_DRAG_MIME);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    if (data?.kind && data?.refId) addContextItem(data);
  } catch {
    loadError.value = "无法解析拖入的素材";
  }
}

function itemKindLabel(kind) {
  if (kind === "resume_draft") return "当前草稿";
  if (kind === "ocr") return "简历";
  if (kind === "job") return "岗位";
  if (kind === "company") return "企业";
  return "素材";
}

function itemKindClass(kind) {
  if (kind === "resume_draft") return "ai-chip--draft";
  if (kind === "ocr") return "ai-chip--ocr";
  if (kind === "job") return "ai-chip--job";
  if (kind === "company") return "ai-chip--company";
  return "";
}

const materialCounts = computed(() => {
  const c = { ocr: 0, job: 0, company: 0 };
  for (const it of contextItems.value) {
    if (c[it.kind] != null) c[it.kind] += 1;
  }
  return c;
});

function buildLeftDraftCard() {
  if (!includeLeftFormEffective.value) return null;
  const title = (props.displayName || "").trim() || "左侧当前简历";
  const subtitle = props.templateId ? `模版 ${props.templateId}` : "当前编辑中";
  return {
    kind: "resume_draft",
    refId: `left-draft-${Date.now()}`,
    title,
    subtitle,
    payload: {
      preview_text: props.leftDraftPreview,
      content: props.leftDraftContent,
      template_id: props.templateId
    }
  };
}

function buildSubmitContextCards() {
  const cards = contextItems.value.map(contextItemToCard);
  const draft = buildLeftDraftCard();
  if (draft) {
    return [contextItemToCard(draft), ...cards];
  }
  return cards;
}

function isItemAdded(kind, refId) {
  return contextItems.value.some((x) => x.kind === kind && x.refId === refId);
}

function addJobFromList(job) {
  addContextItem(jobDragPayload(job));
}

function addCompanyFromList(company) {
  addContextItem(companyDragPayload(company));
}

function formatJobPreviewText(job) {
  if (!job || typeof job !== "object") return "";
  const lines = [];
  const title = job.job_title || job.job_name || job.job_id;
  if (title) lines.push(`岗位名称：${title}`);
  if (job.city || job.district) lines.push(`工作地点：${[job.city, job.district].filter(Boolean).join(" ")}`);
  const company = job.company_relation?.company_name || job.company_name;
  if (company) lines.push(`招聘企业：${company}`);
  if (job.salary || job.salary_range) lines.push(`薪资：${job.salary || job.salary_range}`);
  if (job.education) lines.push(`学历：${job.education}`);
  const desc =
    job.job_desc ||
    job.job_description ||
    job.description ||
    job.requirement ||
    job.job_requirement;
  if (desc) lines.push("", String(desc).trim());
  return lines.join("\n").trim();
}

function formatCompanyPreviewText(company) {
  if (!company || typeof company !== "object") return "";
  const lines = [];
  if (company.company_name) lines.push(`企业名称：${company.company_name}`);
  if (company.industry) lines.push(`行业：${company.industry}`);
  if (company.credit_code) lines.push(`统一社会信用代码：${company.credit_code}`);
  const intro = company.intro || company.description || company.company_intro;
  if (intro) lines.push("", String(intro).trim());
  return lines.join("\n").trim();
}

function formatItemPreviewBody(item) {
  const payload = item.payload;
  if (item.kind === "ocr") return String(payload?.text || "").trim();
  if (item.kind === "job") return formatJobPreviewText(payload);
  if (item.kind === "company") return formatCompanyPreviewText(payload);
  return "";
}

const canPreview = computed(
  () =>
    contextItems.value.length > 0 ||
    !!supplementalNotes.value.trim() ||
    includeLeftFormEffective.value
);

/** 汇总左侧草稿（若勾选）、素材篮与补充说明，供预览展示 */
const materialsPreviewText = computed(() => {
  const blocks = [];
  if (includeLeftFormEffective.value) {
    blocks.push(
      `【左侧当前简历草稿 · 优化基准】\n${String(props.leftDraftPreview || "").trim()}`
    );
  }
  for (const item of contextItems.value) {
    const label = itemKindLabel(item.kind);
    const head = `【${label}】${item.title}${item.subtitle ? ` · ${item.subtitle}` : ""}`;
    const body = formatItemPreviewBody(item);
    blocks.push(body ? `${head}\n${body}` : head);
  }
  const notes = supplementalNotes.value.trim();
  if (notes) blocks.push(`【补充说明】\n${notes}`);
  if (!blocks.length) {
    return "（素材篮暂无内容）\n\n请先通过 OCR 解析简历、添加收藏岗位/关注企业，或填写补充说明。";
  }
  const summary = [];
  if (includeLeftFormEffective.value) summary.push("含左侧表单基准");
  const c = materialCounts.value;
  if (c.ocr) summary.push(`简历 ${c.ocr} 项`);
  if (c.job) summary.push(`岗位 ${c.job} 项`);
  if (c.company) summary.push(`企业 ${c.company} 项`);
  if (notes) summary.push("含补充说明");
  const itemCount = contextItems.value.length + (includeLeftFormEffective.value ? 1 : 0);
  const header = `—— 共 ${itemCount} 项${summary.length ? `（${summary.join("，")}）` : ""} ——`;
  return `${header}\n\n${blocks.join("\n\n────────────────\n\n")}`;
});

function togglePreview() {
  if (!canPreview.value) return;
  previewVisible.value = !previewVisible.value;
}

async function loadFavoritesAndFollows() {
  loadError.value = "";
  favoriteJobs.value = [];
  followedCompanies.value = [];
  if (!sid.value) return;
  loading.value = true;
  const q = new URLSearchParams({ student_id: sid.value });
  try {
    const [fav, fol] = await Promise.all([
      apiGet(`/api/me/favorites?${q}`),
      apiGet(`/api/me/follows?${q}`)
    ]);
    favoriteJobs.value = fav?.jobs || [];
    followedCompanies.value = fol?.companies || [];
  } catch (e) {
    loadError.value = e.message || "加载收藏与关注失败";
  } finally {
    loading.value = false;
  }
}

function contextItemToCard(item) {
  return {
    type: item.kind,
    ref_id: item.refId,
    title: item.title || item.refId,
    subtitle: item.subtitle || "",
    payload: item.payload
  };
}

function resumeSessionStorageKey(studentId) {
  return `resume_ai_session_${studentId}`;
}

async function ensureResumeChatSession(studentId) {
  const key = resumeSessionStorageKey(studentId);
  let sessionId = localStorage.getItem(key);
  if (!sessionId) {
    sessionId = `${studentId}-resume-ai-${Date.now()}`;
  }
  try {
    await apiPost("/api/chat-sessions/init", {
      session_id: sessionId,
      student_id: studentId,
      usercode: RESUME_OPTIMIZER_USERCODE
    });
    localStorage.setItem(key, sessionId);
  } catch (e) {
    const msg = String(e?.message || "");
    if (!/已存在|exist/i.test(msg)) {
      throw e;
    }
    localStorage.setItem(key, sessionId);
  }
  return sessionId;
}

function onResumeRenderPayload(payload) {
  dispatchResumeRender(payload);
  emit("resume-render", payload);
}

async function handleSubmit() {
  if (!canSubmit.value) return;
  const studentId = sid.value;
  if (!studentId) {
    submitMessage.value = "请先关联学号";
    return;
  }

  streamAbortController?.abort();
  streamAbortController = new AbortController();
  submitState.value = "submitting";
  submitMessage.value = "正在调用简历优化师生成内容…";

  const withLeft = includeLeftFormEffective.value;
  const displayMessage =
    supplementalNotes.value.trim() ||
    (withLeft
      ? "请以上方【左侧当前简历草稿】为基准，结合素材篮优化各分段；保留结构与已有事实，输出可更新左侧表单的完整简历 JSON。"
      : "请根据素材篮与附加上下文，生成完整简历并填入各分段。");
  const contextCards = buildSubmitContextCards();
  const hiddenContext = supplementalNotes.value.trim();

  let resumeFilled = false;

  try {
    const sessionId = await ensureResumeChatSession(studentId);
    await apiPostSse(
      `/api/chat-sessions/${encodeURIComponent(sessionId)}/messages/stream`,
      {
        message: displayMessage,
        message_context: hiddenContext,
        context_cards: contextCards,
        student_id: studentId,
        use_role_pipeline: false,
        use_adversarial_harness: false,
        adversarial_desc: ""
      },
      {
        signal: streamAbortController.signal,
        onEvent: (eventName, data) => {
          if (eventName === "resume_render" && data && typeof data === "object") {
            resumeFilled = true;
            onResumeRenderPayload(data);
          }
          if (eventName === "done" && data?.resume_render) {
            resumeFilled = true;
            onResumeRenderPayload(data.resume_render);
          }
          if (eventName === "error") {
            throw new Error(data?.detail || "流式生成失败");
          }
        }
      }
    );
    submitState.value = "done";
    submitMessage.value = resumeFilled
      ? withLeft
        ? "已按左侧表单基准优化并填入编辑器，请核对后保存。"
        : "已生成并填入左侧简历编辑器，请核对后保存。"
      : "优化师已回复建议（未触发整份简历生成）；可勾选左侧表单或补充「生成简历」说明后重试。";
  } catch (e) {
    if (e?.name === "AbortError") return;
    submitState.value = "error";
    submitMessage.value = e.message || "AI 优化请求失败";
  } finally {
    streamAbortController = null;
    setTimeout(() => {
      if (submitState.value === "done" || submitState.value === "error") {
        submitState.value = "idle";
      }
    }, 8000);
  }
}

function clearAll() {
  if (!contextItems.value.length && !supplementalNotes.value.trim()) return;
  if (!confirm("清空全部优化素材与补充说明？")) return;
  contextItems.value = [];
  supplementalNotes.value = "";
  submitMessage.value = "";
  submitState.value = "idle";
  previewVisible.value = false;
}

function onIncludeLeftFormChange() {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(INCLUDE_LEFT_FORM_KEY, includeLeftForm.value ? "1" : "0");
}

let unsubscribeResumeAiContext = () => {};

onMounted(() => {
  loadFavoritesAndFollows();
  unsubscribeResumeAiContext = subscribeResumeAiContext((item) => {
    addContextItem(item);
  });
});
watch(sid, () => loadFavoritesAndFollows());
watch(leftDraftReady, (ready) => {
  if (!ready) includeLeftForm.value = false;
});
onBeforeUnmount(() => {
  unsubscribeResumeAiContext();
  streamAbortController?.abort();
  streamAbortController = null;
});
</script>

<template>
  <aside class="ai-rail" :class="{ 'ai-rail--embedded': embedded }" aria-label="AI 简历优化">
    <header v-if="embedded" class="ai-hero">
    
      <div class="ai-hero-stats" aria-label="素材统计">
        <span class="ai-stat-pill" :class="{ 'ai-stat-pill--on': materialCounts.ocr > 0 }">简历 {{ materialCounts.ocr }}</span>
        <span class="ai-stat-pill ai-stat-pill--job" :class="{ 'ai-stat-pill--on': materialCounts.job > 0 }">岗位 {{ materialCounts.job }}</span>
        <span class="ai-stat-pill ai-stat-pill--co" :class="{ 'ai-stat-pill--on': materialCounts.company > 0 }">企业 {{ materialCounts.company }}</span>
      </div>
    </header>

    <header v-else class="ai-rail-head">
      <div class="ai-rail-head-text">
        <h2 class="ai-rail-title">
          <span class="ai-rail-spark" aria-hidden="true">✦</span>
          AI 简历优化
        </h2>
        <p class="ai-rail-sub">汇集 OCR、意向岗位与企业信息，生成后自动填入左侧简历</p>
      </div>
    </header>

    <div class="ai-rail-scroll">
      <p v-if="guest" class="ai-rail-guest">请先在页面关联学号并登录，以加载收藏岗位与关注企业。</p>
      <p v-else-if="loadError" class="ai-rail-error">{{ loadError }}</p>

      <section class="ai-section ai-section--drop">
        <div class="ai-section-head">
          <h3 class="ai-section-title">
            <span class="ai-section-icon" aria-hidden="true">◎</span>
            优化素材篮
          </h3>
          <span class="ai-section-meta">{{ contextSummary }}</span>
        </div>
        <div
          class="ai-drop-zone"
          :class="{ 'ai-drop-zone--active': dropActive, 'ai-drop-zone--empty': !contextItems.length }"
          @dragover="onDropZoneDragOver"
          @dragleave="onDropZoneDragLeave"
          @drop="onDropZoneDrop"
        >
          <div v-if="!contextItems.length" class="ai-drop-empty">
            <span class="ai-drop-empty-icon" aria-hidden="true">↓</span>
            <p class="ai-drop-hint">将下方岗位/企业<strong>拖入</strong>或<strong>点击添加</strong></p>
            <p class="ai-drop-hint-sub">完成 OCR 识别后会自动加入素材篮</p>
          </div>
          <ul v-else class="ai-chip-list">
            <li v-for="item in contextItems" :key="item.id" class="ai-chip" :class="itemKindClass(item.kind)">
              <span class="ai-chip-badge">{{ itemKindLabel(item.kind) }}</span>
              <div class="ai-chip-body">
                <span class="ai-chip-title">{{ item.title }}</span>
                <span v-if="item.subtitle" class="ai-chip-sub">{{ item.subtitle }}</span>
              </div>
              <button type="button" class="ai-chip-remove" title="移除" @click="removeItem(item.id)">×</button>
            </li>
          </ul>
        </div>
        <div v-if="contextItems.length" class="ai-drop-actions">
          <button type="button" class="ai-link-btn" @click="clearAll">清空素材篮</button>
        </div>
      </section>

      <details class="ai-fold ai-fold--ocr" open>
        <summary class="ai-fold-summary">
          <span class="ai-fold-badge ai-fold-badge--ocr">1</span>
          <span class="ai-fold-title">解析上传简历</span>
          <span class="ai-fold-chevron" aria-hidden="true">›</span>
        </summary>
        <div class="ai-fold-body ai-fold-body--ocr">
          <p class="ai-fold-hint">支持图片、PDF、Word，拖拽或选择文件即可识别</p>
          <div class="ai-ocr-wrap">
            <OcrView compact hide-language-option @recognized="onOcrRecognized" />
          </div>
        </div>
      </details>

      <details class="ai-fold ai-fold--job">
        <summary class="ai-fold-summary">
          <span class="ai-fold-badge ai-fold-badge--job">2</span>
          <span class="ai-fold-title">收藏岗位</span>
          <span class="ai-fold-stat">{{ favList.length }} 个</span>
          <span class="ai-fold-chevron" aria-hidden="true">›</span>
        </summary>
        <div class="ai-fold-body">
          <p v-if="loading" class="ai-rail-muted">加载中…</p>
          <template v-else>
            <p v-if="favList.length" class="ai-fold-hint">点击「添加」或拖动到素材篮</p>
            <ul v-if="favList.length" class="ai-mini-list ai-mini-list--scroll">
              <li
                v-for="j in favList"
                :key="j.job_id"
                class="ai-mini-item ai-mini-item--job"
                :class="{ 'ai-mini-item--added': isItemAdded('job', j.job_id) }"
                draggable="true"
                @dragstart="onDragStart($event, jobDragPayload(j))"
              >
                <div class="ai-mini-body">
                  <span class="ai-mini-title">{{ j.job_title || j.job_id }}</span>
                  <span class="ai-mini-meta">
                    {{ j.city || "" }}
                    <template v-if="j.company_relation?.company_name"> · {{ j.company_relation.company_name }}</template>
                  </span>
                </div>
                <button
                  v-if="!isItemAdded('job', j.job_id)"
                  type="button"
                  class="ai-mini-add"
                  @click="addJobFromList(j)"
                >添加</button>
                <span v-else class="ai-mini-added">已添加</span>
              </li>
            </ul>
            <p v-else class="ai-empty">暂无收藏，可在岗位列表中收藏后刷新</p>
          </template>
        </div>
      </details>

      <details class="ai-fold ai-fold--company">
        <summary class="ai-fold-summary">
          <span class="ai-fold-badge ai-fold-badge--company">3</span>
          <span class="ai-fold-title">关注企业</span>
          <span class="ai-fold-stat">{{ folList.length }} 家</span>
          <span class="ai-fold-chevron" aria-hidden="true">›</span>
        </summary>
        <div class="ai-fold-body">
          <p v-if="loading" class="ai-rail-muted">加载中…</p>
          <template v-else>
            <p v-if="folList.length" class="ai-fold-hint">点击「添加」或拖动到素材篮</p>
            <ul v-if="folList.length" class="ai-mini-list ai-mini-list--scroll">
              <li
                v-for="c in folList"
                :key="c.credit_code"
                class="ai-mini-item ai-mini-item--company"
                :class="{ 'ai-mini-item--added': isItemAdded('company', c.credit_code) }"
                draggable="true"
                @dragstart="onDragStart($event, companyDragPayload(c))"
              >
                <div class="ai-mini-body">
                  <span class="ai-mini-title">{{ c.company_name || c.credit_code }}</span>
                  <span v-if="c.industry" class="ai-mini-meta">{{ c.industry }}</span>
                </div>
                <button
                  v-if="!isItemAdded('company', c.credit_code)"
                  type="button"
                  class="ai-mini-add"
                  @click="addCompanyFromList(c)"
                >添加</button>
                <span v-else class="ai-mini-added">已添加</span>
              </li>
            </ul>
            <p v-else class="ai-empty">暂无关注，可在企业列表中关注后刷新</p>
          </template>
        </div>
      </details>

      <section class="ai-section ai-section--notes">
        <div class="ai-section-head">
          <span class="ai-fold-badge ai-fold-badge--notes">4</span>
          <h3 class="ai-section-title">补充说明</h3>
        </div>
        <label class="ai-notes-field">
          <span class="sr-only">补充说明</span>
          <textarea
            v-model="supplementalNotes"
            rows="3"
            placeholder="希望突出的能力、项目亮点、投递场景等"
          />
        </label>
      </section>
    </div>

    <section v-if="previewVisible" class="ai-preview-panel" aria-label="素材文本预览">
      <div class="ai-preview-head">
        <h3 class="ai-preview-title">素材预览</h3>
        <button type="button" class="ai-preview-close" @click="previewVisible = false">收起</button>
      </div>
      <p class="ai-preview-hint muted small">以下为将提交优化的参考文本汇总（只读）</p>
      <pre class="ai-preview-body">{{ materialsPreviewText }}</pre>
    </section>

    <footer class="ai-rail-footer">
      <label class="ai-include-left" :class="{ 'ai-include-left--disabled': !leftDraftReady }">
        <input
          v-model="includeLeftForm"
          type="checkbox"
          :disabled="!leftDraftReady"
          @change="onIncludeLeftFormChange"
        />
        <span>添加左侧表单信息（与实时预览一致，作为优化基准）</span>
      </label>
      <p v-if="includeLeftForm && !leftDraftReady" class="ai-include-left-hint muted small">
        左侧表单暂无内容，请先填写基本信息或分段后再勾选。
      </p>
      <div class="ai-footer-actions">
        <button
          type="button"
          class="ai-preview-btn"
          :disabled="!canPreview"
          :aria-expanded="previewVisible"
          @click="togglePreview"
        >
          {{ previewVisible ? "收起预览" : "预览将提交内容" }}
        </button>
        <button
          type="button"
          class="ai-submit-btn"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          <span v-if="submitState === 'submitting'">生成中…</span>
          <span v-else>提交优化</span>
        </button>
      </div>
      <p v-if="submitMessage" class="ai-submit-msg">{{ submitMessage }}</p>
      <p v-else-if="!canSubmit && !guest" class="ai-submit-hint muted small">
        请勾选左侧表单、添加素材，或填写补充说明后提交
      </p>
      <button
        v-if="!guest"
        type="button"
        class="ai-refresh-btn"
        :disabled="loading"
        @click="loadFavoritesAndFollows"
      >刷新岗位与企业</button>
    </footer>
  </aside>
</template>
<style scoped>
.ai-rail {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  gap: 0;
  background: #f8fafc;
}
.ai-rail--embedded {
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  background: transparent;
}
.ai-hero {
  flex-shrink: 0;
  padding: 12px 14px 10px;
  border-bottom: 1px solid #ede9fe;
  background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 55%, #fff 100%);
}
.ai-hero-desc {
  margin: 0 0 10px;
  font-size: 0.78rem;
  color: #6b7280;
  line-height: 1.45;
}
.ai-hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ai-stat-pill {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  color: #9ca3af;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}
.ai-stat-pill--on {
  color: #5b21b6;
  background: #ede9fe;
  border-color: #c4b5fd;
}
.ai-stat-pill--job.ai-stat-pill--on {
  color: #b45309;
  background: #ffedd5;
  border-color: #fdba74;
}
.ai-stat-pill--co.ai-stat-pill--on {
  color: #047857;
  background: #d1fae5;
  border-color: #6ee7b7;
}
.ai-rail-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 12px 14px 20px;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.ai-rail-scroll > * + * {
  margin-top: 10px;
}
.ai-rail-head {
  flex-shrink: 0;
  padding: 14px 14px 0;
}
.ai-rail-head-text { min-width: 0; }
.ai-rail-title {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 800;
  color: #581c87;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ai-rail-spark { font-size: 0.85rem; color: #a855f7; }
.ai-rail-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: #6b7280;
  line-height: 1.45;
}
.ai-rail-guest, .ai-rail-muted {
  margin: 0;
  font-size: 0.82rem;
  color: #6b7280;
  line-height: 1.5;
}
.ai-rail-error { margin: 0; font-size: 0.82rem; color: #dc2626; }
.ai-section { flex-shrink: 0; }
.ai-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.ai-section-title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ai-section-icon { color: #a855f7; font-size: 0.75rem; }
.ai-section-meta { font-size: 0.68rem; color: #9ca3af; text-align: right; }
.ai-section--drop {
  position: sticky;
  top: 0;
  z-index: 4;
  padding: 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e9d5ff;
  box-shadow: 0 4px 16px rgba(124, 58, 237, 0.06);
}
.ai-drop-zone {
  border: 2px dashed #d8b4fe;
  border-radius: 12px;
  padding: 10px;
  min-height: 64px;
  background: #faf5ff;
  transition: border-color 0.15s, background 0.15s;
}
.ai-drop-zone--active { border-color: #a855f7; background: #f3e8ff; }
.ai-drop-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 6px 4px;
}
.ai-drop-empty-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #ede9fe;
  color: #7c3aed;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  font-weight: 800;
  margin-bottom: 6px;
}
.ai-drop-hint { margin: 0; font-size: 0.76rem; color: #6b7280; line-height: 1.45; }
.ai-drop-hint strong { color: #7c3aed; font-weight: 600; }
.ai-drop-hint-sub { margin: 4px 0 0; font-size: 0.7rem; color: #9ca3af; }
.ai-chip-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.ai-chip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e5e7eb;
}
.ai-chip--ocr { border-color: #c7d2fe; background: #f8fafc; }
.ai-chip--job { border-color: #fed7aa; background: #fffbeb; }
.ai-chip--company { border-color: #a7f3d0; background: #ecfdf5; }
.ai-chip-badge {
  flex-shrink: 0;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 6px;
}
.ai-chip--ocr .ai-chip-badge { color: #4338ca; background: #e0e7ff; }
.ai-chip--job .ai-chip-badge { color: #b45309; background: #ffedd5; }
.ai-chip--company .ai-chip-badge { color: #047857; background: #d1fae5; }
.ai-chip-body { flex: 1; min-width: 0; }
.ai-chip-title { display: block; font-size: 0.8rem; font-weight: 600; color: #1f2937; line-height: 1.35; }
.ai-chip-sub { display: block; margin-top: 2px; font-size: 0.7rem; color: #6b7280; }
.ai-chip-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #9ca3af;
  font-size: 1.1rem;
  cursor: pointer;
}
.ai-chip-remove:hover { background: #fee2e2; color: #dc2626; }
.ai-drop-actions { margin-top: 6px; text-align: right; }
.ai-link-btn {
  border: none;
  background: none;
  color: #7c3aed;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}
.ai-link-btn:hover { text-decoration: underline; }
.ai-fold {
  flex-shrink: 0;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  overflow: visible;
}
.ai-fold-summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  user-select: none;
}
.ai-fold-summary::-webkit-details-marker { display: none; }
.ai-fold[open] .ai-fold-chevron { transform: rotate(90deg); }
.ai-fold[open] .ai-fold-summary {
  border-bottom: 1px solid #f1f5f9;
}
.ai-fold[open] + .ai-fold,
.ai-fold[open] + .ai-section,
.ai-section + .ai-fold[open] {
  margin-top: 10px;
}
.ai-fold-badge {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 800;
  color: #fff;
}
.ai-fold-badge--ocr { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.ai-fold-badge--job { background: linear-gradient(135deg, #f59e0b, #f97316); }
.ai-fold-badge--company { background: linear-gradient(135deg, #10b981, #059669); }
.ai-fold-badge--notes { background: linear-gradient(135deg, #64748b, #475569); }
.ai-fold-title { flex: 1; font-size: 0.84rem; font-weight: 700; color: #1f2937; }
.ai-fold-stat { font-size: 0.72rem; color: #6b7280; font-weight: 600; }
.ai-fold-chevron { flex-shrink: 0; font-size: 1rem; color: #9ca3af; transition: transform 0.2s; }
.ai-fold-body {
  padding: 0 10px 12px;
  overflow: visible;
}
.ai-fold-body--ocr {
  padding-bottom: 14px;
}
.ai-fold-hint { margin: 0 0 8px; font-size: 0.72rem; color: #6b7280; }
.ai-ocr-wrap {
  border-radius: 10px;
  overflow: visible;
  border: 1px solid #e5e7eb;
  background: #fff;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .link-row),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .pane-title),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .history-wrap),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .raw-wrap),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .toolbar),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .result-list) {
  display: none;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact) {
  overflow: visible;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .wrap) {
  padding: 0;
  overflow: visible;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .panel) {
  border: none;
  box-shadow: none;
  padding: 10px;
  overflow: visible;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .row) {
  grid-template-columns: 1fr !important;
  gap: 10px;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .upload-wrap) {
  margin-top: 8px;
  padding: 12px;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .aggregate) {
  max-height: 140px;
  overflow-y: auto;
  font-size: 0.72rem;
  margin-top: 8px;
  -webkit-overflow-scrolling: touch;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .preview-image) {
  max-height: 140px;
}
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .summary),
.ai-rail--embedded .ai-ocr-wrap :deep(.ocr-root--compact .error) {
  margin: 8px 0 0;
  font-size: 0.75rem;
}
.ai-mini-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
/* 展开岗位/企业时列表区域可独立滚动 */
.ai-mini-list--scroll {
  max-height: min(240px, 42vh);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding-right: 2px;
}
.ai-rail--embedded .ai-fold-body .ai-mini-list--scroll {
  max-height: min(200px, 36vh);
}
.ai-mini-item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #eceff3;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  cursor: grab;
  transition: border-color 0.15s, background 0.15s;
}
.ai-mini-item:active { cursor: grabbing; }
.ai-mini-item--added { opacity: 0.72; background: #f9fafb; }
.ai-mini-body { flex: 1; min-width: 0; }
.ai-mini-title { display: block; font-size: 0.8rem; font-weight: 600; color: #1f2937; line-height: 1.35; }
.ai-mini-meta { display: block; margin-top: 2px; font-size: 0.7rem; color: #6b7280; }
.ai-mini-add {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #c4b5fd;
  background: #f5f3ff;
  color: #7c3aed;
  font-size: 0.68rem;
  font-weight: 700;
  cursor: pointer;
}
.ai-mini-add:hover { background: #ede9fe; }
.ai-mini-added {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  color: #059669;
}
.ai-mini-item--job:hover:not(.ai-mini-item--added) { border-color: #fdba74; }
.ai-mini-item--company:hover:not(.ai-mini-item--added) { border-color: #6ee7b7; }
.ai-empty { margin: 0; font-size: 0.76rem; color: #9ca3af; }
.ai-section--notes {
  padding: 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
}
.ai-section--notes .ai-section-head { margin-bottom: 6px; }
.ai-notes-field textarea {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.84rem;
  font-family: inherit;
  resize: vertical;
  min-height: 72px;
  background: #fafafa;
  box-sizing: border-box;
}
.ai-notes-field textarea:focus {
  outline: 2px solid #c084fc;
  outline-offset: 1px;
  border-color: #a855f7;
  background: #fff;
}
.ai-rail-footer {
  flex-shrink: 0;
  padding: 10px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid #e5e7eb;
  background: linear-gradient(180deg, rgba(255,255,255,0.92) 0%, #fff 100%);
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.06);
}
.ai-include-left {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.82rem;
  color: #334155;
  cursor: pointer;
  line-height: 1.45;
}
.ai-include-left--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ai-include-left input {
  margin-top: 3px;
  flex-shrink: 0;
}
.ai-include-left-hint {
  margin: -4px 0 0;
}
.ai-footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ai-chip--draft {
  border-color: #a5b4fc;
  background: #eef2ff;
}
.ai-rail--embedded .ai-rail-footer {
  flex-shrink: 0;
  background: #fff;
}
.ai-preview-panel {
  flex-shrink: 0;
  max-height: min(42vh, 320px);
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e9d5ff;
  background: #fff;
  box-shadow: 0 -6px 20px rgba(124, 58, 237, 0.08);
}
.ai-preview-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px 6px;
}
.ai-preview-title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #5b21b6;
}
.ai-preview-close {
  border: 1px solid #e9d5ff;
  background: #faf5ff;
  color: #7c3aed;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.ai-preview-close:hover {
  background: #f3e8ff;
}
.ai-preview-hint {
  flex-shrink: 0;
  margin: 0;
  padding: 0 14px 6px;
}
.ai-preview-body {
  flex: 1;
  min-height: 80px;
  margin: 0;
  padding: 10px 14px 12px;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  font-size: 0.76rem;
  line-height: 1.55;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f8fafc;
  border-top: 1px solid #f1f5f9;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.ai-preview-btn {
  width: 100%;
  padding: 10px 16px;
  border-radius: 11px;
  border: 1px solid #c4b5fd;
  background: #faf5ff;
  color: #6d28d9;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.ai-preview-btn:hover:not(:disabled) {
  background: #f3e8ff;
  border-color: #a78bfa;
}
.ai-preview-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.ai-submit-btn {
  width: 100%;
  padding: 11px 16px;
  border: none;
  border-radius: 11px;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.3);
  transition: opacity 0.15s, transform 0.15s;
}
.ai-submit-btn:hover:not(:disabled) { transform: translateY(-1px); }
.ai-submit-btn:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.ai-submit-msg {
  margin: 0;
  font-size: 0.76rem;
  color: #059669;
  padding: 8px 10px;
  background: #ecfdf5;
  border-radius: 8px;
  border: 1px solid #a7f3d0;
}
.ai-submit-hint { margin: 0; text-align: center; }
.ai-refresh-btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 10px;
  padding: 7px;
  font-size: 0.74rem;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
}
.ai-refresh-btn:hover:not(:disabled) { border-color: #c084fc; color: #7c3aed; }
.ai-refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.muted { color: var(--text-muted, #6b7280); }
.small { font-size: 0.78rem; }
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
</style>