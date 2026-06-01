<script setup>
/**
 * 面试大纲右侧面板：二级行业下的大纲 CRUD 列表。
 */
import InterviewPlanListCard from "./InterviewPlanListCard.vue";

defineProps({
  industry: { type: Object, default: null },
  plans: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  guest: { type: Boolean, default: false }
});

defineEmits(["create", "edit", "delete"]);
</script>

<template>
  <section class="plan-panel">
    <header v-if="industry" class="panel-head">
      <div class="head-text">
        <span class="level-tag">二级行业</span>
        <h2>{{ industry.path }}</h2>
        <p class="hint">点击卡片查看详情 · 共 {{ plans.length }} 个大纲</p>
      </div>
      <button type="button" class="plan-btn plan-btn-primary" :disabled="guest" @click="$emit('create')">
        + 新增大纲
      </button>
    </header>

    <p v-if="guest" class="state warn">
      请先<router-link to="/login">登录</router-link>后管理大纲。
    </p>
    <p v-else-if="!industry" class="state">请从左侧展开并选择<strong>二级行业</strong>，查看与管理题目大纲。</p>
    <p v-else-if="loading" class="state">加载大纲中…</p>
    <p v-else-if="error" class="state error">{{ error }}</p>
    <p v-else-if="!plans.length" class="state">该二级行业下暂无大纲，点击「新增大纲」创建。</p>

    <ul v-else class="plan-list">
      <InterviewPlanListCard
        v-for="p in plans"
        :key="p.plan_row_id"
        :item="p"
        @edit="(planId, version) => $emit('edit', planId, version)"
        @delete="(planId) => $emit('delete', planId)"
      />
    </ul>
  </section>
</template>

<style scoped>
.plan-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.panel-head {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #eceff3;
  background: linear-gradient(180deg, #fafbff, #fff);
}

.head-text h2 {
  margin: 6px 0 0;
  font-size: 1.05rem;
  color: #1f2937;
}

.level-tag {
  font-size: 0.72rem;
  font-weight: 700;
  background: #ecfdf5;
  color: #047857;
  padding: 2px 8px;
  border-radius: 999px;
}

.hint {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: #6b7280;
}

.plan-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  list-style: none;
  margin: 0;
  padding: 14px 16px 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 12px;
  align-content: start;
}

.plan-btn {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  font-family: inherit;
  white-space: nowrap;
}

.plan-btn-primary {
  background: #6366f1;
  color: #fff;
}

.plan-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.state {
  padding: 48px 20px;
  text-align: center;
  color: #6b7280;
  font-size: 0.9rem;
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
