<script setup>
/**
 * 题目大纲详情 — 基础信息、版本切换、模块标签与可交互题目列表。
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PlanBasicInfoPanel from "../components/interview/PlanBasicInfoPanel.vue";
import PlanQuestionCardList from "../components/interview/PlanQuestionCardList.vue";
import PlanVersionSelect from "../components/interview/PlanVersionSelect.vue";
import { getStudentId } from "../api/client";
import { fetchInterviewPlanDetail } from "../modules/interview/api";
import { formatDateTime } from "../modules/interview/formatters";
import { PLAN_STATUS } from "../modules/interview/constants";

const route = useRoute();
const router = useRouter();
const detail = ref(null);
const loadError = ref("");

const currentVersion = computed(() => detail.value?.version ?? null);

function statusLabel(s) {
  return PLAN_STATUS[s]?.label || s || "—";
}

async function load() {
  const sid = getStudentId();
  const planId = route.params.planId;
  if (!sid || !planId) {
    loadError.value = "请先登录";
    return;
  }
  loadError.value = "";
  try {
    const version = route.query.version ? Number(route.query.version) : undefined;
    detail.value = await fetchInterviewPlanDetail(sid, planId, version);
    syncRouteVersion(detail.value?.version);
  } catch (e) {
    loadError.value = e.message || "加载失败";
    detail.value = null;
  }
}

/** URL 未带 version 时补全 query，便于分享链接定位到当前版本 */
function syncRouteVersion(version) {
  if (version == null || route.query.version) {
    return;
  }
  router.replace({
    query: { ...route.query, version: String(version) }
  });
}

function onVersionChange(nextVersion) {
  if (nextVersion == null || String(route.query.version) === String(nextVersion)) {
    return;
  }
  router.push({
    query: { ...route.query, version: String(nextVersion) }
  });
}

onMounted(load);
watch(() => [route.params.planId, route.query.version], load);
</script>

<template>
  <div class="detail-page">
    <section class="hero">
      <p class="hero-kicker">面试大纲</p>
      <h1>{{ detail?.title || detail?.target_role || "大纲详情" }}</h1>
      <p v-if="detail" class="hero-meta">
        {{ statusLabel(detail.status) }} · v{{ detail.version }} · {{ detail.questions?.length || 0 }} 题
        · {{ formatDateTime(detail.created_at) }}
      </p>
      <PlanVersionSelect
        v-if="detail?.versions?.length"
        :versions="detail.versions"
        :model-value="currentVersion"
        @update:model-value="onVersionChange"
      />
    </section>

    <div class="container">
      <p v-if="loadError" class="error">{{ loadError }}</p>
      <template v-else-if="detail">
        <PlanBasicInfoPanel :detail="detail" />

        <section class="panel q-panel">
          <header class="q-panel-head">
            <h2>题目列表</h2>
            <span class="q-count">共 {{ detail.questions?.length || 0 }} 题</span>
          </header>
          <PlanQuestionCardList :questions="detail.questions || []" :page-size="12" interactive />
        </section>

        <router-link class="back" to="/interview/industry">← 返回列表</router-link>
      </template>
      <p v-else class="muted">加载中…</p>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 240px);
}

.hero {
  padding: 88px 20px 20px;
  text-align: center;
}

.hero-kicker {
  margin: 0 0 6px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6366f1;
}

.hero h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #111827;
}

.hero-meta {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 0.88rem;
}

.container {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 18px 80px;
}

.panel {
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.q-panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.q-panel-head h2 {
  margin: 0;
}

.q-count {
  font-size: 0.82rem;
  color: #6b7280;
}

.back {
  color: #6366f1;
  font-weight: 600;
  text-decoration: none;
}

.muted {
  color: #6b7280;
  text-align: center;
}

.error {
  color: #dc2626;
  font-weight: 600;
}
</style>
