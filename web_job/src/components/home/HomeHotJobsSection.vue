<script setup>
/**
 * 首页「热招职位」横向卡片列表。
 */
import { computed } from "vue";

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
});

const emit = defineEmits(["view-detail", "view-more"]);

const displayJobs = computed(() => (props.jobs || []).slice(0, 4));

function normalizeJob(item) {
  return {
    job_id: item.id || item.job_id,
    job_title: item.jobName || item.job_title || "-",
    city: item.address || item.city || "-",
    area: item.area || item.district || "",
    salary: item.salaryRange || item.salary_range_month || "面议",
    company: item.companyName || item.company_relation?.company_name || "-",
    industry: item.job_hylb || item.industry || "互联网"
  };
}

const items = computed(() => displayJobs.value.map(normalizeJob));
</script>

<template>
  <section class="hot-section card-panel">
    <header class="hot-head">
      <h2>热招职位</h2>
      <button type="button" class="link-btn" @click="emit('view-more')">查看更多</button>
    </header>

    <div v-if="loading" class="hot-loading">加载热招岗位…</div>

    <div v-else-if="!items.length" class="hot-loading">暂无热招岗位</div>

    <div v-else class="hot-list">
      <article
        v-for="job in items"
        :key="job.job_id"
        class="hot-card"
        role="button"
        tabindex="0"
        @click="emit('view-detail', job)"
        @keydown.enter.prevent="emit('view-detail', job)"
      >
        <div class="hot-card-top">
          <h3>{{ job.job_title }}</h3>
          <span class="hot-salary">{{ job.salary }}</span>
        </div>
        <div class="hot-tags">
          <span class="hot-tag">{{ job.city }}</span>
          <span v-if="job.area" class="hot-tag">{{ job.area }}</span>
        </div>
        <p class="hot-meta">{{ job.company }} · {{ job.industry }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.hot-section {
  margin-top: 14px;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border);
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px 18px;
}
.hot-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.hot-head h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}
.link-btn {
  border: none;
  background: none;
  color: #5b6adf;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.hot-loading {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 0.86rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
}
.hot-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
@media (max-width: 1280px) {
  .hot-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 900px) {
  .hot-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.hot-card {
  background: #fff;
  border: 1px solid rgba(91, 106, 223, 0.08);
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.hot-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 6px 18px rgba(91, 106, 223, 0.1);
}
.hot-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.hot-card-top h3 {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}
.hot-salary {
  flex-shrink: 0;
  color: #ea580c;
  font-size: 0.82rem;
  font-weight: 700;
}
.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}
.hot-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.68rem;
}
.hot-meta {
  margin: 0;
  font-size: 0.72rem;
  color: #94a3b8;
}
@media (max-width: 900px) {
  .hot-list {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .job-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
