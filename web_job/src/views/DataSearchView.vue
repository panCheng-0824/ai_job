<script setup>
import { ref } from "vue";
import { apiGet } from "../api/client";

const props = defineProps({
  compact: { type: Boolean, default: false }
});
const query = ref("");
const engine = ref("baidu");
const topk = ref(5);
const deepSearch = ref(false);
const loading = ref(false);
const error = ref("");
const summary = ref("输入关键词后开始搜索");
const items = ref([]);
let thinkingTimer = null;
let thinkingStartTs = 0;

async function runSearch() {
  if (!query.value.trim()) {
    error.value = "请输入搜索问题";
    return;
  }
  error.value = "";
  loading.value = true;
  startThinkingTimer();
  try {
    const data = await apiGet(`/api/online-search?query=${encodeURIComponent(query.value.trim())}&engine=${encodeURIComponent(engine.value)}&topk=${topk.value}&deep_search=${deepSearch.value ? "true" : "false"}`);
    items.value = data.items || [];
    stopThinkingTimer(`已检索 ${data.count || 0} 条结果（引擎：${data.engine || engine.value}，模式：${data.deep_search ? "深度搜索" : "普通搜索"}）`);
  } catch (err) {
    stopThinkingTimer("搜索失败");
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function startThinkingTimer() {
  if (thinkingTimer) {
    clearInterval(thinkingTimer);
    thinkingTimer = null;
  }
  thinkingStartTs = Date.now();
  const render = () => {
    const elapsedSec = ((Date.now() - thinkingStartTs) / 1000).toFixed(1);
    summary.value = `搜索中，请稍候...（思考时间：${elapsedSec}s）`;
  };
  render();
  thinkingTimer = setInterval(render, 100);
}

function stopThinkingTimer(prefix) {
  if (!thinkingStartTs) return;
  if (thinkingTimer) {
    clearInterval(thinkingTimer);
    thinkingTimer = null;
  }
  const elapsedSec = ((Date.now() - thinkingStartTs) / 1000).toFixed(1);
  summary.value = `${prefix}（思考时间：${elapsedSec}s）`;
  thinkingStartTs = 0;
}
</script>

<template>
  <div class="ds-root" :class="{ 'ds-root--compact': props.compact }">
    <section v-if="!props.compact" class="hero">
      <h1>数据搜索</h1>
      <p>参考 online_search 逻辑，抓取搜索结果并提取正文。</p>
    </section>
    <div class="container">
      <section class="panel">
        <h2 v-if="props.compact" class="pane-title">数据搜索</h2>
        <div class="form-line">
          <input v-model="query" class="field" placeholder="输入搜索问题，例如：人工智能就业趋势" @keydown.enter.prevent="runSearch" />
          <select v-model="engine" class="select">
            <option value="baidu">baidu</option>
            <option value="duckduckgo">duckduckgo</option>
          </select>
          <input v-model.number="topk" class="field" type="number" min="1" max="10" />
          <button class="btn" :disabled="loading" @click="runSearch">{{ loading ? "搜索中..." : "开始搜索" }}</button>
        </div>
        <label class="switch-line"><input v-model="deepSearch" type="checkbox" /> 启用深度搜索（访问结果链接并提取正文，耗时更长）</label>
        <p class="tip" id="summary">{{ summary }}</p>
        <p class="error">{{ error }}</p>
        <ul class="result-list">
          <li v-if="!items.length" class="item">暂无结果</li>
          <li v-for="(item, idx) in items" v-else :key="idx" class="item">
            <a :href="item.url || '#'" target="_blank" rel="noopener noreferrer">{{ item.title || "无标题" }}</a>
            <div class="meta">排名：{{ item.rank || "-" }} ｜ 来源：{{ item.url || "-" }}</div>
            <div class="meta">摘要：{{ item.snippet || "无摘要" }}</div>
            <div class="body">{{ (item.body || "").slice(0, 1000) || "正文为空" }}</div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ds-root--compact .container {
  padding: 0;
  max-width: 100%;
}
.ds-root--compact .panel {
  border-radius: 14px;
  box-shadow: none;
  border: 1px solid #e5e7eb;
  padding: 14px;
}
.pane-title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #374151;
}
.hero { padding: 86px 20px 40px; text-align: center; background: radial-gradient(circle at top right, #eef2ff, transparent), radial-gradient(circle at top left, #f5f3ff, transparent); }
.hero p { color: var(--text-muted); }
.container { max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
.form-line { display: grid; grid-template-columns: 1fr 130px 90px auto; gap: 10px; margin-bottom: 10px; }
.switch-line { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--text-muted); font-size: .9rem; }
.tip { color: var(--text-muted); font-size: .88rem; margin-bottom: 12px; }
.error { font-size: .9rem; margin-bottom: 8px; }
.result-list { list-style: none; display: grid; gap: 12px; padding: 0; }
.ds-root--compact .result-list {
  max-height: min(48vh, 420px);
  overflow-y: auto;
  padding-right: 4px;
}
.item { border: 1px solid #eceff3; border-radius: 12px; padding: 12px; background: #fff; }
.item a { color: var(--primary-color); text-decoration: none; font-weight: 600; font-size: .96rem; }
.meta { color: var(--text-muted); font-size: .84rem; margin-top: 4px; }
.body { color: #374151; font-size: .88rem; line-height: 1.55; margin-top: 8px; white-space: pre-wrap; }
@media (max-width: 980px) { .form-line { grid-template-columns: 1fr; } }
</style>
