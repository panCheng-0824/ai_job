<script setup>
/**
 * 题目大纲详情弹窗 — 壳层与编辑弹窗一致，内容为只读基础信息与题目列表。
 */
import { computed } from "vue";
import PlanBasicInfoPanel from "./PlanBasicInfoPanel.vue";
import PlanQuestionCardList from "./PlanQuestionCardList.vue";
import PlanVersionSelect from "./PlanVersionSelect.vue";
import { formatDateTime } from "../../modules/interview/formatters";
import { PLAN_STATUS } from "../../modules/interview/constants";

const props = defineProps({
  visible: { type: Boolean, default: false },
  detail: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  guest: { type: Boolean, default: false }
});

const emit = defineEmits(["close", "edit", "version-change"]);

const currentVersion = computed(() => props.detail?.version ?? null);

const heroTitle = computed(
  () => props.detail?.title || props.detail?.target_role || "大纲详情"
);

const heroMeta = computed(() => {
  if (!props.detail) return "";
  const status = PLAN_STATUS[props.detail.status]?.label || props.detail.status || "—";
  const count = props.detail.questions?.length || 0;
  const date = formatDateTime(props.detail.created_at);
  return `${status} · v${props.detail.version} · ${count} 题 · ${date}`;
});

function onVersionChange(version) {
  emit("version-change", version);
}

function onEdit() {
  if (!props.detail) return;
  emit("edit", props.detail.plan_id, props.detail.version);
}
</script>

<template>
  <div v-if="visible" class="overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="plan-detail-title">
      <header class="modal-head">
        <div class="head-main">
          <h2 id="plan-detail-title">{{ heroTitle }}</h2>
          <p v-if="detail" class="plan-meta">{{ heroMeta }}</p>
          <PlanVersionSelect
            v-if="detail?.versions?.length"
            :versions="detail.versions"
            :model-value="currentVersion"
            @update:model-value="onVersionChange"
          />
        </div>
        <button type="button" class="icon-btn" aria-label="关闭" @click="$emit('close')">×</button>
      </header>

      <div class="modal-body">
        <p v-if="guest" class="state warn">
          请先<router-link to="/login">登录</router-link>后查看大纲详情。
        </p>
        <p v-else-if="error" class="state error">{{ error }}</p>
        <p v-else-if="loading" class="state">加载大纲详情…</p>
        <template v-else-if="detail">
          <PlanBasicInfoPanel class="info-panel-embedded" :detail="detail" />

          <section class="q-panel">
            <header class="q-panel-head">
              <h3>题目列表</h3>
              <span class="q-count">共 {{ detail.questions?.length || 0 }} 题</span>
            </header>
            <PlanQuestionCardList :questions="detail.questions || []" :page-size="12" interactive />
          </section>
        </template>
      </div>

      <footer class="actions">
        <button type="button" class="plan-btn plan-btn-ghost" @click="$emit('close')">关闭</button>
        <button
          v-if="detail && !guest"
          type="button"
          class="plan-btn plan-btn-primary"
          @click="onEdit"
        >
          编辑
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 14000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal {
  width: min(920px, 100%);
  max-height: 92vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #eceff3;
  flex-shrink: 0;
}

.head-main {
  min-width: 0;
  flex: 1;
}

.modal-head h2 {
  margin: 0;
  font-size: 1.05rem;
  word-break: break-word;
}

.plan-meta {
  margin: 4px 0 0;
  font-size: 0.76rem;
  color: #6b7280;
}

.icon-btn {
  border: none;
  background: transparent;
  font-size: 1.4rem;
  cursor: pointer;
  color: #6b7280;
  flex-shrink: 0;
}

.modal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 18px;
  display: grid;
  gap: 12px;
  align-content: start;
  -webkit-overflow-scrolling: touch;
}

.info-panel-embedded {
  margin-bottom: 0;
}

.q-panel {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 14px 16px;
  background: #fafbff;
}

.q-panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.q-panel-head h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #1f2937;
}

.q-count {
  font-size: 0.82rem;
  color: #6b7280;
}

.actions {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid #eceff3;
  background: #fff;
}

.plan-btn {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  font-family: inherit;
}

.plan-btn-ghost {
  background: #f3f4f6;
  color: #374151;
}

.plan-btn-primary {
  background: #6366f1;
  color: #fff;
}

.state {
  margin: 0;
  text-align: center;
  color: #6b7280;
  font-size: 0.88rem;
  padding: 32px 12px;
}

.state.warn,
.state.error {
  font-weight: 600;
}

.state.error {
  color: #dc2626;
}

.state a {
  color: #6366f1;
}
</style>
