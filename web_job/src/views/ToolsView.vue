<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataSearchView from "./DataSearchView.vue";
import OcrView from "./OcrView.vue";

const route = useRoute();
const router = useRouter();
const tab = ref(route.query.tab === "ocr" ? "ocr" : "search");
const isEmbed = computed(() => route.query._embed === "1");

watch(
  () => route.query.tab,
  (t) => {
    if (t === "ocr") tab.value = "ocr";
    else tab.value = "search";
  }
);

/** 切换标签时保留 _embed 等查询参数，避免浮层内嵌页变成整页布局 */
function setTab(next) {
  tab.value = next;
  const query = { ...route.query };
  query.tab = next === "ocr" ? "ocr" : "search";
  router.replace({ path: "/tools", query });
}
</script>

<template>
  <div class="tools-page" :class="{ 'tools-page--embed': isEmbed }">
    <div class="tools-dock">
      <header class="dock-head">
        <div class="dock-brand">
          <span class="dock-icon" aria-hidden="true">✦</span>
          <div>
            <h1 class="dock-title">工具箱</h1>
          </div>
        </div>
        <nav class="dock-tabs" role="tablist" aria-label="工具切换">
          <button
            type="button"
            role="tab"
            :aria-selected="tab === 'search'"
            class="dock-tab"
            :class="{ active: tab === 'search' }"
            @click="setTab('search')"
          >
            数据搜索
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="tab === 'ocr'"
            class="dock-tab"
            :class="{ active: tab === 'ocr' }"
            @click="setTab('ocr')"
          >
            OCR 识别
          </button>
        </nav>
      </header>
      <div class="dock-body">
        <section v-show="tab === 'search'" class="dock-pane" :aria-hidden="tab !== 'search'">
          <DataSearchView compact />
        </section>
        <section v-show="tab === 'ocr'" class="dock-pane" :aria-hidden="tab !== 'ocr'">
          <OcrView compact />
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tools-page {
  min-height: 100vh;
  padding: 88px 20px 32px;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.12), transparent),
    radial-gradient(ellipse 60% 40% at 100% 50%, rgba(168, 85, 247, 0.06), transparent),
    #f1f5f9;
}
.tools-dock {
  max-width: 980px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: min(78vh, 720px);
}
.dock-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 24px;
  padding: 18px 20px 16px;
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
  border-bottom: 1px solid #eceff3;
}
.dock-brand {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}
.dock-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}
.dock-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #111827;
}
.dock-sub {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: #6b7280;
  line-height: 1.45;
  max-width: 36rem;
}
.dock-tabs {
  display: inline-flex;
  padding: 4px;
  border-radius: 14px;
  background: #eef2ff;
  border: 1px solid rgba(99, 102, 241, 0.2);
  gap: 4px;
}
.dock-tab {
  border: none;
  background: transparent;
  color: #4b5563;
  font-size: 0.88rem;
  font-weight: 600;
  padding: 8px 18px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}
.dock-tab:hover {
  color: #4338ca;
  background: rgba(255, 255, 255, 0.65);
}
.dock-tab.active {
  background: #fff;
  color: #4338ca;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.18);
}
.dock-body {
  flex: 1;
  min-height: 0;
  padding: 16px 18px 20px;
  background: #f8fafc;
  overflow: auto;
}
.dock-pane {
  max-width: 100%;
}
.tools-page--embed {
  min-height: 100%;
  padding: 0;
  background: #f8fafc;
}
.tools-page--embed .tools-dock {
  max-width: none;
  margin: 0;
  min-height: 100%;
  border-radius: 0;
  border: none;
  box-shadow: none;
}
@media (max-width: 640px) {
  .tools-page:not(.tools-page--embed) {
    padding: 80px 12px 20px;
  }
  .dock-head {
    flex-direction: column;
    align-items: stretch;
  }
  .dock-tabs {
    width: 100%;
    justify-content: stretch;
  }
  .dock-tab {
    flex: 1;
    text-align: center;
  }
}
</style>
