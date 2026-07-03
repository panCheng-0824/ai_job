<script setup>
/**
 * 岗位中心「热门企业」Tab 网格；查看详情由父级弹框展示（对齐热招职位）。
 */
import { computed } from "vue";

const props = defineProps({
  companies: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false }
});

const emit = defineEmits(["view-detail"]);

const items = computed(() =>
  (props.companies || []).map((item) => ({
    raw: item,
    credit_code: item.credit_code || item.id || item.company_id,
    company_name: item.company_name || item.companyName || "-",
    industry: item.industry || item.area || "—",
    company_size: item.company_size || item.companySize || item.employee_count_range || "—",
    job_count: Number(item.job_count ?? item.jobCount ?? 0)
  }))
);

function onViewDetail(item) {
  if (!item?.credit_code) return;
  emit("view-detail", {
    credit_code: item.credit_code,
    company_name: item.company_name,
    industry: item.industry,
    company_size: item.company_size,
    job_count: item.job_count,
    ...item.raw
  });
}
</script>

<template>
  <section class="jobs-center-panel">
    <div v-if="loading" class="jobs-loading">加载企业中…</div>
    <div v-else-if="!items.length" class="jobs-empty">暂无热门企业</div>
    <div v-else class="company-grid">
      <article
        v-for="item in items"
        :key="item.credit_code"
        class="company-card"
        role="button"
        tabindex="0"
        @click="onViewDetail(item)"
        @keydown.enter.prevent="onViewDetail(item)"
      >
        <h3>{{ item.company_name }}</h3>
        <p class="company-meta">{{ item.industry }} · {{ item.company_size }}</p>
        <p class="company-jobs">在招岗位 {{ item.job_count }} 个</p>
        <div class="company-actions" @click.stop>
          <button type="button" class="company-btn" @click="onViewDetail(item)">查看详情</button>
        </div>
      </article>
    </div>
    <slot name="after-grid" />
  </section>
</template>

<style scoped>
.jobs-center-panel {
  min-width: 0;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border);
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px 18px;
}
.jobs-center-head {
  margin-bottom: 14px;
}
.jobs-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.jobs-loading,
.jobs-empty {
  min-height: 220px;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 0.88rem;
}
.company-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.company-card {
  border: 1px solid rgba(91, 106, 223, 0.1);
  border-radius: 12px;
  padding: 14px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.company-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 8px 20px rgba(91, 106, 223, 0.1);
}
.company-card h3 {
  margin: 0 0 6px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #0f172a;
}
.company-meta {
  margin: 0 0 8px;
  font-size: 0.76rem;
  color: #64748b;
}
.company-jobs {
  margin: 0 0 10px;
  font-size: 0.74rem;
  color: #4338ca;
  font-weight: 600;
}
.company-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.company-btn {
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
  color: #4338ca;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}

.company-btn:hover {
  background: #eef2ff;
}
@media (max-width: 1100px) {
  .company-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .company-grid { grid-template-columns: 1fr; }
}
</style>
