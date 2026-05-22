<script setup>
/**
 * 对话助手右侧「我的资料」：简历 / 收藏岗位 / 关注企业。
 * 岗位规划师（ROLE001）、简历优化师（ROLE004）共用；卡片可拖入输入框附加上下文。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import FloatingFramePanel from "./FloatingFramePanel.vue";
import { apiGet } from "../api/client";
import { fetchResumeStore } from "../modules/resume/api";
import { pickSeriesDefaultVersion, stripTimeCopySuffix } from "../modules/resume/storage";
import { embedUrl, fullPageUrl } from "../utils/embedFrame";
import { setContextRailVisible } from "../composables/useChatPlannerRailVisible";
import { CONTEXT_DRAG_MIME } from "../constants/contextDrag";

const props = defineProps({
  studentId: { type: String, default: "" },
  /** 用于侧栏隐藏时写入对应角色的展开状态 */
  usercode: { type: String, default: "ROLE001" }
});

/** 侧栏展开区内列表最大高度，超出滚动（不截断条数） */
const LIST_MAX_HEIGHT = "min(280px, 36vh)";

const loading = ref(false);
const loadError = ref("");
const resumeGroups = ref([]);
const favoriteJobs = ref([]);
const followedCompanies = ref([]);

const frameOpen = ref(false);
const frameFullscreen = ref(false);
const iframeSrc = ref("");
const frameTitle = ref("");

const sid = computed(() => (props.studentId || "").trim());
const guest = computed(() => !sid.value);

const primaryResume = computed(() => {
  const list = resumeGroups.value || [];
  const global = list.find((g) => g.isGlobalSeries);
  return global || list[0] || null;
});

const resumePreviewLines = computed(() => {
  const r = primaryResume.value?.latest;
  if (!r?.content) return [];
  const c = r.content;
  const lines = [];
  const name = c.basic?.name || c.basic?.姓名;
  if (name) lines.push(`姓名：${name}`);
  const school = c.basic?.school || c.basic?.学校;
  if (school) lines.push(`院校：${school}`);
  const tj = c.intent?.targetJobs;
  if (tj) lines.push(`意向：${String(tj).slice(0, 48)}${String(tj).length > 48 ? "…" : ""}`);
  if (!lines.length) lines.push(stripTimeCopySuffix(r.displayName || "") || "点击查看或编辑简历");
  return lines;
});

const favList = computed(() => favoriteJobs.value || []);
const folList = computed(() => followedCompanies.value || []);

function closeFrame() {
  frameOpen.value = false;
  frameFullscreen.value = false;
  iframeSrc.value = "";
  frameTitle.value = "";
}

function openFrame(path, label, extraQuery = {}) {
  const q = { ...extraQuery };
  if (sid.value) q.student_id = sid.value;
  frameTitle.value = label;
  iframeSrc.value = embedUrl(path, q);
  frameOpen.value = true;
  frameFullscreen.value = false;
}

function toggleFullscreen() {
  frameFullscreen.value = !frameFullscreen.value;
}

function openFullWindow() {
  if (!iframeSrc.value) return;
  window.open(fullPageUrl(iframeSrc.value), "_blank", "noopener,noreferrer");
}

function openResumeEditor() {
  openFrame("/resume/create", "我的简历");
}

function openFavoritesPage() {
  openFrame("/me", "我的收藏", { tab: "fav" });
}

function openFollowsPage() {
  openFrame("/me", "我的关注", { tab: "fol" });
}

function openJobDetail(job) {
  if (!job?.job_id) return;
  const title = job.job_title || job.job_name || job.job_id;
  openFrame(`/jobs/${encodeURIComponent(job.job_id)}`, title);
}

function openCompanyDetail(company) {
  const code = company?.credit_code;
  if (!code) return;
  const title = company.company_name || code;
  openFrame(`/companies/${encodeURIComponent(code)}`, title);
}

function onDragRef(ev, ref) {
  if (!ref?.ref_id) return;
  ev.dataTransfer.setData(CONTEXT_DRAG_MIME, JSON.stringify(ref));
  ev.dataTransfer.effectAllowed = "copy";
}

function resumeDragRef() {
  const g = primaryResume.value;
  if (!g) return null;
  const r = g.latest;
  if (!r) return null;
  return {
    type: "resume",
    ref_id: r.id,
    title: g.label,
    subtitle: resumePreviewLines.value[0] || "",
    variant: "resume"
  };
}

function jobDragRef(job) {
  return {
    type: "job",
    ref_id: job.job_id,
    title: job.job_title || job.job_name || job.job_id,
    subtitle: `${job.city || ""} ${job.company_relation?.company_name || ""}`.trim(),
    variant: "fav"
  };
}

function companyDragRef(c) {
  return {
    type: "company",
    ref_id: c.credit_code,
    title: c.company_name || c.credit_code,
    subtitle: c.industry || "",
    variant: "fol"
  };
}

function groupResumes(resumes, defaultResumeId) {
  const list = Array.isArray(resumes) ? resumes : [];
  const map = new Map();
  for (const r of list) {
    const key = r.seriesId || r.id;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(r);
  }
  const groups = [];
  for (const [seriesId, versions] of map) {
    versions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    const latest = pickSeriesDefaultVersion(versions, defaultResumeId) || versions[0];
    const label = stripTimeCopySuffix(latest?.displayName || "") || "简历";
    const isGlobalSeries = versions.some((v) => v.id === defaultResumeId);
    groups.push({ seriesId, label, versions, latest, isGlobalSeries });
  }
  groups.sort((a, b) => {
    if (a.isGlobalSeries !== b.isGlobalSeries) return a.isGlobalSeries ? -1 : 1;
    return (b.latest?.updatedAt || 0) - (a.latest?.updatedAt || 0);
  });
  return groups;
}

async function loadAll() {
  loadError.value = "";
  resumeGroups.value = [];
  favoriteJobs.value = [];
  followedCompanies.value = [];
  if (!sid.value) return;
  loading.value = true;
  const q = new URLSearchParams({ student_id: sid.value });
  try {
    const [store, fav, fol] = await Promise.all([
      fetchResumeStore(sid.value),
      apiGet(`/api/me/favorites?${q}`),
      apiGet(`/api/me/follows?${q}`)
    ]);
    resumeGroups.value = groupResumes(store?.resumes, store?.defaultResumeId);
    favoriteJobs.value = fav?.jobs || [];
    followedCompanies.value = fol?.companies || [];
  } catch (e) {
    loadError.value = e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

function onDocKey(ev) {
  if (ev.key === "Escape" && frameOpen.value) closeFrame();
}

onMounted(() => {
  document.addEventListener("keydown", onDocKey);
  loadAll();
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onDocKey);
});

watch(sid, () => loadAll());

defineExpose({ reload: loadAll });
</script>

<template>
  <aside class="planner-rail" aria-label="我的资料">
    <div class="planner-rail-head">
      <div class="planner-rail-head-text">
        <h2 class="planner-rail-title">我的资料</h2>
        <p class="planner-rail-sub">拖入对话框作为附加上下文</p>
      </div>
      <button type="button" class="planner-rail-hide-btn" title="隐藏右侧资料栏" @click="setContextRailVisible(usercode, false)">
        收起
      </button>
    </div>

    <p v-if="guest" class="planner-rail-guest">
      请先在左侧填写学号并登录，以加载简历、收藏与关注。
    </p>
    <p v-else-if="loadError" class="planner-rail-error">{{ loadError }}</p>
    <p v-else-if="loading" class="planner-rail-muted">加载中…</p>

    <template v-else-if="!guest">
      <!-- 简历（默认收起） -->
      <details class="ctx-fold">
        <summary class="ctx-fold-summary">
          <div
            class="ctx-card ctx-card--resume ctx-card--compact"
            draggable="true"
            @dragstart.stop="resumeDragRef() && onDragRef($event, resumeDragRef())"
          >
            <span class="ctx-card-badge">简历</span>
            <span class="ctx-card-title">
              {{ primaryResume ? primaryResume.label : "暂无简历" }}
            </span>
            <span class="ctx-card-stat">
              {{ resumeGroups.length ? `${resumeGroups.length} 份` : "点击展开" }}
            </span>
            <span class="ctx-fold-chevron" aria-hidden="true">›</span>
          </div>
        </summary>
        <div class="ctx-fold-body">
          <ul v-if="resumePreviewLines.length" class="ctx-card-lines">
            <li v-for="(line, i) in resumePreviewLines" :key="'r-' + i">{{ line }}</li>
          </ul>
          <p v-else class="ctx-empty">暂无简历内容，可前往创建</p>
          <button type="button" class="ctx-fold-action" @click="openResumeEditor">打开简历编辑</button>
        </div>
      </details>

      <!-- 收藏岗位（默认收起） -->
      <details class="ctx-fold">
        <summary class="ctx-fold-summary">
          <div class="ctx-card ctx-card--fav ctx-card--compact">
            <span class="ctx-card-badge">收藏</span>
            <span class="ctx-card-title">收藏岗位</span>
            <span class="ctx-card-stat">{{ favoriteJobs.length }} 个</span>
            <span class="ctx-fold-chevron" aria-hidden="true">›</span>
          </div>
        </summary>
        <div class="ctx-fold-body">
          <p v-if="favList.length" class="ctx-fold-hint">共 {{ favList.length }} 个，可拖动到输入框</p>
          <ul v-if="favList.length" class="ctx-mini-list ctx-mini-list--scroll">
            <li
              v-for="j in favList"
              :key="j.job_id"
              class="ctx-mini-item"
              role="button"
              tabindex="0"
              draggable="true"
              @dragstart="onDragRef($event, jobDragRef(j))"
              @click="openJobDetail(j)"
              @keydown.enter.prevent="openJobDetail(j)"
            >
              <span class="ctx-mini-title">{{ j.job_title || j.job_id }}</span>
              <span class="ctx-mini-meta">
                {{ j.city || "" }} {{ j.district || "" }}
                <template v-if="j.company_relation?.company_name">
                  ｜ {{ j.company_relation.company_name }}
                </template>
              </span>
            </li>
          </ul>
          <p v-else class="ctx-empty">暂无收藏，可在岗位列表中收藏</p>
          <button
            v-if="favList.length"
            type="button"
            class="ctx-fold-action"
            @click="openFavoritesPage"
          >
            在「我的」中查看全部收藏
          </button>
        </div>
      </details>

      <!-- 关注企业（默认收起） -->
      <details class="ctx-fold">
        <summary class="ctx-fold-summary">
          <div class="ctx-card ctx-card--fol ctx-card--compact">
            <span class="ctx-card-badge">关注</span>
            <span class="ctx-card-title">关注企业</span>
            <span class="ctx-card-stat">{{ followedCompanies.length }} 家</span>
            <span class="ctx-fold-chevron" aria-hidden="true">›</span>
          </div>
        </summary>
        <div class="ctx-fold-body">
          <p v-if="folList.length" class="ctx-fold-hint">共 {{ folList.length }} 家，可拖动到输入框</p>
          <ul v-if="folList.length" class="ctx-mini-list ctx-mini-list--scroll">
            <li
              v-for="c in folList"
              :key="c.credit_code"
              class="ctx-mini-item"
              role="button"
              tabindex="0"
              draggable="true"
              @dragstart="onDragRef($event, companyDragRef(c))"
              @click="openCompanyDetail(c)"
              @keydown.enter.prevent="openCompanyDetail(c)"
            >
              <span class="ctx-mini-title">{{ c.company_name || c.credit_code }}</span>
              <span v-if="c.industry" class="ctx-mini-meta">{{ c.industry }}</span>
            </li>
          </ul>
          <p v-else class="ctx-empty">暂无关注，可在企业列表中关注</p>
          <button
            v-if="folList.length"
            type="button"
            class="ctx-fold-action"
            @click="openFollowsPage"
          >
            在「我的」中查看全部关注
          </button>
        </div>
      </details>
    </template>

    <button v-if="!guest" type="button" class="ctx-refresh" :disabled="loading" @click="loadAll">
      刷新资料
    </button>
  </aside>

  <Teleport to="body">
    <FloatingFramePanel
      :open="frameOpen"
      :fullscreen="frameFullscreen"
      :title="frameTitle"
      :z-index="13150"
      @backdrop-click="closeFrame"
    >
      <template #actions>
        <button type="button" @click="toggleFullscreen">{{ frameFullscreen ? "缩小" : "放大" }}</button>
        <button type="button" @click="openFullWindow">完整页面</button>
        <button type="button" class="danger" @click="closeFrame">关闭</button>
      </template>
      <iframe v-if="iframeSrc" :title="frameTitle" :src="iframeSrc" />
    </FloatingFramePanel>
  </Teleport>
</template>

<style scoped>
.planner-rail {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 18px;
  box-shadow: 0 18px 34px rgba(0, 0, 0, 0.06);
  padding: 14px 12px;
  overflow: auto;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  -webkit-overflow-scrolling: touch;
}
.planner-rail-head {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.planner-rail-head-text {
  min-width: 0;
  flex: 1;
}
.planner-rail-hide-btn {
  flex-shrink: 0;
  border: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
}
.planner-rail-hide-btn:hover {
  border-color: #c7d2fe;
  color: #4338ca;
  background: #fff;
}
.planner-rail-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #1e293b;
}
.planner-rail-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: #6b7280;
}
.planner-rail-guest,
.planner-rail-muted {
  font-size: 0.82rem;
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}
.planner-rail-error {
  font-size: 0.82rem;
  color: #dc2626;
  margin: 0;
}
.ctx-fold {
  border-radius: 14px;
  overflow: hidden;
}
.ctx-fold-summary {
  list-style: none;
  cursor: pointer;
  user-select: none;
}
.ctx-fold-summary::-webkit-details-marker {
  display: none;
}
.ctx-fold[open] .ctx-fold-chevron {
  transform: rotate(90deg);
}
.ctx-fold-body {
  padding: 4px 4px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ctx-fold-hint {
  margin: 0;
  font-size: 0.72rem;
  color: #6b7280;
}
.ctx-mini-list--scroll {
  max-height: v-bind(LIST_MAX_HEIGHT);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-right: 2px;
}
.ctx-fold-chevron {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #6b7280;
  line-height: 1;
  transition: transform 0.2s ease;
}
.ctx-fold-action {
  align-self: flex-start;
  border: 1px solid rgba(99, 102, 241, 0.35);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.76rem;
  font-weight: 600;
  color: #4338ca;
  cursor: pointer;
}
.ctx-fold-action:hover {
  background: #fff;
  border-color: #6366f1;
}
.ctx-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  width: 100%;
  text-align: left;
  border: none;
  border-radius: 14px;
  padding: 12px 12px 10px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  box-sizing: border-box;
}
.ctx-card--compact {
  padding: 10px 10px 8px;
}
.ctx-fold-summary:hover .ctx-card {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
}
.ctx-card--resume {
  background: linear-gradient(145deg, #eef2ff 0%, #e0e7ff 55%, #ddd6fe 100%);
  border: 1px solid rgba(99, 102, 241, 0.35);
}
.ctx-card--fav {
  background: linear-gradient(145deg, #fff7ed 0%, #ffedd5 55%, #fde68a 100%);
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.ctx-card--fol {
  background: linear-gradient(145deg, #ecfdf5 0%, #d1fae5 55%, #a7f3d0 100%);
  border: 1px solid rgba(16, 185, 129, 0.35);
}
.ctx-card-badge {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.65);
  color: #374151;
}
.ctx-card--resume .ctx-card-badge {
  color: #4338ca;
}
.ctx-card--fav .ctx-card-badge {
  color: #b45309;
}
.ctx-card--fol .ctx-card-badge {
  color: #047857;
}
.ctx-card-title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.35;
}
.ctx-card-stat {
  font-size: 0.76rem;
  color: #4b5563;
  font-weight: 600;
  flex-shrink: 0;
}
.ctx-card-lines {
  margin: 0;
  padding: 0 0 0 1rem;
  font-size: 0.76rem;
  color: #374151;
  line-height: 1.45;
}
.ctx-mini-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ctx-mini-item {
  border: 1px solid #eceff3;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  cursor: grab;
  transition: border-color 0.15s, background 0.15s;
}
.ctx-mini-item:active {
  cursor: grabbing;
}
.ctx-card[draggable="true"] {
  cursor: grab;
}
.ctx-card[draggable="true"]:active {
  cursor: grabbing;
}
.ctx-mini-item:hover {
  border-color: #c7d2fe;
  background: #f8fafc;
}
.ctx-mini-item:focus {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}
.ctx-mini-title {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.35;
}
.ctx-mini-meta {
  display: block;
  margin-top: 3px;
  font-size: 0.72rem;
  color: #6b7280;
  line-height: 1.35;
}
.ctx-empty {
  margin: 0;
  font-size: 0.76rem;
  color: #9ca3af;
  padding: 4px 2px;
}
.ctx-more {
  align-self: flex-start;
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 0;
}
.ctx-more:hover {
  text-decoration: underline;
}
.ctx-refresh {
  margin-top: auto;
  flex-shrink: 0;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 10px;
  padding: 8px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
}
.ctx-refresh:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #c7d2fe;
  color: #4338ca;
}
.ctx-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
