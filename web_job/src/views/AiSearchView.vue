<script setup>
/**
 * 工具箱 — 智能搜索：URL + 自然语言流式采集。
 */
import { computed, nextTick, ref, watch } from "vue";
import { apiPostNdjsonStream } from "../api/client";

const props = defineProps({
  compact: { type: Boolean, default: false }
});

const url = ref("");
const prompt = ref("");
const mode = ref("scrapy");
const maxPages = ref(5);
const followLinks = ref(false);
const activePane = ref("log");

const loading = ref(false);
const error = ref("");
const result = ref(null);
const stepLogs = ref([]);
const elapsedSec = ref(0);
const logPanelRef = ref(null);

let elapsedTimer = null;

const MODES = [
  { id: "scrapy", label: "HTTP", desc: "静态页" },
  { id: "drission", label: "浏览器", desc: "动态页" },
  { id: "auto", label: "自动", desc: "智能选" }
];

const pageCount = computed(() => result.value?.pages?.length || 0);
const meta = computed(() => result.value?.meta || {});

const progressPct = computed(() => {
  if (!loading.value) return result.value ? 100 : 0;
  return Math.min(92, 18 + stepLogs.value.length * 6);
});

const statusText = computed(() => {
  if (loading.value) return "正在采集…";
  if (error.value) return "采集失败";
  if (result.value) return `完成 · ${pageCount.value} 页`;
  return "等待开始";
});

watch(stepLogs, async () => {
  await nextTick();
  const el = logPanelRef.value;
  if (el) el.scrollTop = el.scrollHeight;
});

watch(result, (val) => {
  if (val?.pages?.length) activePane.value = "result";
});

function startTimer() {
  stopTimer();
  elapsedSec.value = 0;
  elapsedTimer = setInterval(() => {
    elapsedSec.value = Number((elapsedSec.value + 0.1).toFixed(1));
  }, 100);
}

function stopTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
}

function resetAll() {
  if (loading.value) return;
  url.value = "";
  prompt.value = "";
  mode.value = "scrapy";
  maxPages.value = 5;
  followLinks.value = false;
  error.value = "";
  result.value = null;
  stepLogs.value = [];
  elapsedSec.value = 0;
  activePane.value = "log";
}

async function runCrawl() {
  const target = url.value.trim();
  if (!target) {
    error.value = "请输入目标网址";
    return;
  }
  if (!/^https?:\/\//i.test(target)) {
    error.value = "网址需以 http:// 或 https:// 开头";
    return;
  }

  error.value = "";
  loading.value = true;
  result.value = null;
  stepLogs.value = [];
  activePane.value = "log";
  startTimer();

  try {
    await apiPostNdjsonStream("/api/ai-search/crawl/stream", {
      url: target,
      prompt: prompt.value.trim(),
      mode: mode.value,
      max_pages: maxPages.value,
      follow_links: followLinks.value
    }, {
      onEvent(obj) {
        if (!obj?.event) return;
        if (obj.event === "start") {
          stepLogs.value.push(`任务启动 · ${obj.url}`);
        }
        if (obj.event === "log" && obj.message) {
          stepLogs.value.push(obj.message);
        }
        if (obj.event === "result") {
          result.value = { ...(obj.data || {}), meta: obj.meta || {} };
        }
        if (obj.event === "error") {
          throw new Error(obj.detail || "采集失败");
        }
      }
    });
    if (!result.value) throw new Error("未收到采集结果");
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
    stopTimer();
  }
}

function shortLog(line) {
  return String(line || "")
    .replace(/^\[STEP[^\]]*\]\s*/, "")
    .replace(/^\[(INIT|DONE|BROWSER|SCRAPY|LLM|SESSION|OUTPUT|WARN[^\]]*)\]\s*/i, "");
}

function logTag(line) {
  const m = String(line || "").match(/^\[([^\]]+)\]/);
  return m ? m[1].split(/\s/)[0] : "LOG";
}

function formatJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}
</script>

<template>
  <div class="smart-search" :class="{ 'smart-search--compact': compact }">
    <!-- 输入区 -->
    <section class="sheet">
      <div class="sheet-head">
        <div class="sheet-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" stroke-linecap="round" />
          </svg>
        </div>
        <div>
          <h2 class="sheet-title">智能搜索</h2>
          <p class="sheet-sub">输入网址与需求，实时查看步骤并获取结构化内容</p>
        </div>
      </div>

      <div class="field-stack">
        <div class="input-wrap">
          <span class="input-prefix">🔗</span>
          <input
            v-model="url"
            class="input"
            type="url"
            placeholder="https://example.com/page"
            :disabled="loading"
            @keydown.enter.prevent="runCrawl"
          />
        </div>
        <textarea
          v-model="prompt"
          class="input textarea"
          rows="2"
          placeholder="描述要提取的内容，例如：标题、正文摘要、表格字段…"
          :disabled="loading"
        />
      </div>

      <div class="mode-row">
        <span class="mode-label">模式</span>
        <div class="mode-group">
          <button
            v-for="m in MODES"
            :key="m.id"
            type="button"
            class="mode-btn"
            :class="{ active: mode === m.id }"
            :disabled="loading"
            :title="m.desc"
            @click="mode = m.id"
          >
            {{ m.label }}
          </button>
        </div>
      </div>

      <div class="opts-row">
        <label class="opt">
          <span>页数</span>
          <input v-model.number="maxPages" type="number" min="1" max="20" :disabled="loading" />
        </label>
        <label class="opt opt-check">
          <input v-model="followLinks" type="checkbox" :disabled="loading" />
          <span>跟随同站链接</span>
        </label>
      </div>

      <div class="action-row">
        <button type="button" class="btn-run" :disabled="loading" @click="runCrawl">
          <span v-if="loading" class="spinner" />
          {{ loading ? "采集中" : "开始采集" }}
        </button>
        <button type="button" class="btn-ghost" :disabled="loading" @click="resetAll">重置</button>
      </div>

      <div class="progress-wrap">
        <div class="progress-meta">
          <span>{{ statusText }}</span>
          <span v-if="loading || result">{{ elapsedSec.toFixed(1) }}s</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${progressPct}%` }" />
        </div>
      </div>
      <p v-if="error" class="err">{{ error }}</p>
    </section>

    <!-- 输出区 -->
    <section class="output">
      <div class="tabs">
        <button
          type="button"
          class="tab"
          :class="{ active: activePane === 'log' }"
          @click="activePane = 'log'"
        >
          运行日志
          <em v-if="stepLogs.length">{{ stepLogs.length }}</em>
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activePane === 'result' }"
          @click="activePane = 'result'"
        >
          采集结果
          <em v-if="pageCount">{{ pageCount }}</em>
        </button>
      </div>

      <div v-show="activePane === 'log'" ref="logPanelRef" class="pane log-pane">
        <div v-if="!stepLogs.length" class="empty">
          <div class="empty-icon">📋</div>
          <p>步骤日志将在这里实时更新</p>
        </div>
        <ul v-else class="timeline">
          <li v-for="(line, i) in stepLogs" :key="i" class="timeline-item">
            <span class="dot" />
            <div class="timeline-body">
              <span class="tag">{{ logTag(line) }}</span>
              <p>{{ shortLog(line) || line }}</p>
            </div>
          </li>
        </ul>
      </div>

      <div v-show="activePane === 'result'" class="pane result-pane">
        <div v-if="!result?.pages?.length" class="empty">
          <div class="empty-icon">📄</div>
          <p>{{ loading ? "等待结果返回…" : "暂无采集结果" }}</p>
        </div>
        <article v-for="(page, idx) in result?.pages || []" :key="idx" class="page-card">
          <header class="page-head">
            <span class="idx">{{ idx + 1 }}</span>
            <h3>{{ page.title || "未命名页面" }}</h3>
          </header>
          <a class="page-url" :href="page.url" target="_blank" rel="noopener noreferrer">
            {{ page.url }}
          </a>
          <p v-if="page.body" class="page-body">{{ page.body.slice(0, 800) }}{{ page.body.length > 800 ? "…" : "" }}</p>
          <details v-if="page.fields && Object.keys(page.fields).length" class="page-fields">
            <summary>结构化字段</summary>
            <pre>{{ formatJson(page.fields) }}</pre>
          </details>
        </article>
      </div>

      <footer v-if="result && meta.mode_used" class="output-foot">
        <span>{{ meta.mode_used }}</span>
        <span v-if="meta.llm_used">· LLM 已解析</span>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.smart-search {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

/* —— 输入卡片 —— */
.sheet {
  background: #fff;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.06);
}

.sheet-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.sheet-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff;
  flex-shrink: 0;
}

.sheet-icon svg {
  width: 22px;
  height: 22px;
}

.sheet-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.02em;
}

.sheet-sub {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: #9ca3af;
  line-height: 1.4;
}

.field-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafafa;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.input-wrap:focus-within {
  border-color: #a5b4fc;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
  background: #fff;
}

.input-prefix {
  font-size: 1rem;
  opacity: 0.7;
}

.input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 11px 0;
  font-size: 0.9rem;
  color: #1f2937;
  outline: none;
  font-family: inherit;
}

.textarea {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafafa;
  font-size: 0.88rem;
  line-height: 1.5;
  resize: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: inherit;
}

.textarea:focus {
  outline: none;
  border-color: #a5b4fc;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
  background: #fff;
}

.mode-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.mode-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #6b7280;
}

.mode-group {
  display: flex;
  gap: 6px;
  flex: 1;
}

.mode-btn {
  flex: 1;
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.mode-btn:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: #4338ca;
}

.mode-btn.active {
  background: linear-gradient(135deg, #eef2ff, #f5f3ff);
  border-color: #a5b4fc;
  color: #4338ca;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.opts-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.opt {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #4b5563;
}

.opt input[type="number"] {
  width: 52px;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  text-align: center;
  font-size: 0.85rem;
}

.opt-check {
  cursor: pointer;
  user-select: none;
}

.action-row {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.btn-run {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 16px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #7c3aed);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: transform 0.12s, box-shadow 0.12s;
  font-family: inherit;
}

.btn-run:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

.btn-run:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
}

.btn-ghost {
  padding: 11px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  color: #6b7280;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}

.btn-ghost:hover:not(:disabled) {
  border-color: #d1d5db;
  color: #374151;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.progress-wrap {
  margin-top: 14px;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #9ca3af;
  margin-bottom: 6px;
}

.progress-track {
  height: 4px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 99px;
  transition: width 0.35s ease;
}

.err {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: #dc2626;
  font-weight: 500;
}

/* —— 输出区 —— */
.output {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 260px;
  max-height: min(46vh, 400px);
}

.tabs {
  display: flex;
  border-bottom: 1px solid #f1f5f9;
  background: #fafbfc;
}

.tab {
  flex: 1;
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 600;
  color: #9ca3af;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: color 0.15s;
  font-family: inherit;
  position: relative;
}

.tab em {
  font-style: normal;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 99px;
  background: #e5e7eb;
  color: #6b7280;
}

.tab.active {
  color: #4338ca;
}

.tab.active em {
  background: #eef2ff;
  color: #4338ca;
}

.tab.active::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 16%;
  right: 16%;
  height: 2px;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 2px 2px 0 0;
}

.pane {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.empty {
  height: 100%;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #9ca3af;
  text-align: center;
}

.empty-icon {
  font-size: 2rem;
  opacity: 0.5;
}

.empty p {
  margin: 0;
  font-size: 0.85rem;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline-item {
  display: flex;
  gap: 10px;
  padding-bottom: 12px;
  position: relative;
}

.timeline-item:not(:last-child)::before {
  content: "";
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: 0;
  width: 1px;
  background: #e5e7eb;
}

.dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #a5b4fc;
  flex-shrink: 0;
  margin-top: 3px;
  z-index: 1;
}

.timeline-body {
  flex: 1;
  min-width: 0;
}

.tag {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6366f1;
  margin-bottom: 2px;
}

.timeline-body p {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  color: #374151;
  word-break: break-word;
}

.page-card {
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: linear-gradient(180deg, #fff 0%, #fafbff 100%);
}

.page-card:last-child {
  margin-bottom: 0;
}

.page-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.idx {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.page-head h3 {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-url {
  display: block;
  font-size: 0.72rem;
  color: #6366f1;
  text-decoration: none;
  word-break: break-all;
  margin-bottom: 8px;
}

.page-url:hover {
  text-decoration: underline;
}

.page-body {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.55;
  color: #4b5563;
}

.page-fields {
  margin-top: 10px;
}

.page-fields summary {
  font-size: 0.78rem;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
}

.page-fields pre {
  margin: 8px 0 0;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 0.72rem;
  overflow: auto;
  max-height: 140px;
  border: 1px solid #f1f5f9;
}

.output-foot {
  padding: 8px 12px;
  border-top: 1px solid #f1f5f9;
  font-size: 0.72rem;
  color: #9ca3af;
  text-align: center;
  background: #fafbfc;
}

/* 紧凑模式（工具箱 Tab 内） */
.smart-search--compact .sheet-sub {
  display: none;
}

.smart-search--compact .output {
  max-height: min(42vh, 360px);
}

@media (max-width: 520px) {
  .mode-group {
    width: 100%;
  }

  .action-row {
    flex-direction: column;
  }

  .btn-ghost {
    width: 100%;
  }
}
</style>
