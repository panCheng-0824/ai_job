<script setup>
/**
 * 学生画像页右侧栏：求职数据、偏好分析、近期浏览岗位。
 */
import { computed } from "vue";

const props = defineProps({
  summary: { type: Object, default: null },
  favorites: { type: Array, default: () => [] },
  recentJobs: { type: Array, default: () => [] },
  preferenceText: { type: String, default: "" }
});

const emit = defineEmits(["view-job", "view-more"]);

const stats = computed(() => {
  const s = props.summary || {};
  return [
    { label: "投递次数", value: s.application_count ?? 0 },
    { label: "面试次数", value: s.interview_count ?? 0 },
    { label: "收藏岗位", value: s.favorite_job_count ?? 0 },
    { label: "关注企业", value: s.followed_company_count ?? 0 }
  ];
});

function normalizeJob(item) {
  return {
    job_id: item.job_id || item.id,
    job_title: item.job_title || item.jobName || "-",
    city: item.city || item.address || "-",
    salary: item.salary_range_month || item.salaryRange || "面议",
    company: item.company_relation?.company_name || item.companyName || "-",
    tags: [item.city || item.address, "经验不限", "本科"].filter(Boolean)
  };
}

const recentList = computed(() => {
  const fav = (props.favorites || []).slice(0, 3).map(normalizeJob);
  if (fav.length) return fav;
  return (props.recentJobs || []).slice(0, 3).map(normalizeJob);
});
</script>

<template>
  <aside class="profile-rail">
    <section class="rail-card">
      <h3>求职数据</h3>
      <div class="stat-grid">
        <div v-for="item in stats" :key="item.label" class="stat-cell">
          <strong>{{ item.value }}</strong>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </section>

    <section class="rail-card">
      <h3>求职偏好分析</h3>
      <p class="pref-text">{{ preferenceText || "完善专业与求职意向后，系统将生成个性化偏好分析。" }}</p>
    </section>

    <section class="rail-card">
      <div class="rail-head">
        <h3>近期浏览岗位</h3>
        <button type="button" class="link-btn" @click="emit('view-more')">更多</button>
      </div>
      <div v-if="!recentList.length" class="empty">暂无浏览记录</div>
      <article
        v-for="job in recentList"
        :key="job.job_id"
        class="recent-card"
        role="button"
        tabindex="0"
        @click="emit('view-job', job)"
        @keydown.enter.prevent="emit('view-job', job)"
      >
        <div class="recent-top">
          <h4>{{ job.job_title }}</h4>
          <span class="salary">{{ job.salary }}</span>
        </div>
        <div class="recent-tags">
          <span v-for="t in job.tags.slice(0, 3)" :key="t" class="tag">{{ t }}</span>
        </div>
        <p class="recent-meta">{{ job.company }}</p>
      </article>
    </section>
  </aside>
</template>

<style scoped>
.profile-rail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.rail-card {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px;
}
.rail-card h3 {
  margin: 0 0 12px;
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
}
.rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.rail-head h3 {
  margin: 0;
}
.link-btn {
  border: none;
  background: none;
  color: var(--home-primary, #5b6adf);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.stat-cell {
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 10px;
  text-align: center;
}
.stat-cell strong {
  display: block;
  font-size: 1.25rem;
  color: var(--home-primary, #5b6adf);
  font-weight: 800;
}
.stat-cell span {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: #94a3b8;
}
.pref-text {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.78rem;
  line-height: 1.65;
}
.recent-card {
  border: 1px solid #eef2ff;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.recent-card:last-child {
  margin-bottom: 0;
}
.recent-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.08);
}
.recent-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.recent-top h4 {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}
.salary {
  flex-shrink: 0;
  color: var(--home-salary, #f97316);
  font-size: 0.78rem;
  font-weight: 700;
}
.recent-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 4px;
}
.tag {
  padding: 2px 7px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.66rem;
}
.recent-meta {
  margin: 0;
  font-size: 0.72rem;
  color: #94a3b8;
}
.empty {
  padding: 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 0.82rem;
  border: 1px dashed #e2e8f0;
  border-radius: 10px;
}
</style>
