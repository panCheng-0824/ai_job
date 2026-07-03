<script setup>
/**
 * 智能匹配职位卡片：悬停/选中态 + 点击固定；按钮区不触发选中。
 */
import { computed } from "vue";
import JobIdTag from "../jobs/JobIdTag.vue";
import { useJobCompare } from "../../composables/useJobCompare";
import { useJobApplication } from "../../composables/useJobApplication";
import { useJobInterviewBooking } from "../../composables/useJobInterviewBooking";

const props = defineProps({
  job: { type: Object, required: true },
  /** 保留入参供父组件统一传参；卡片内不展示推荐理由正文 */
  recommendation: { type: Object, default: null },
  active: { type: Boolean, default: false },
  hover: { type: Boolean, default: false },
  pinned: { type: Boolean, default: false }
});

const emit = defineEmits(["view-detail", "apply", "resume", "interview", "hover", "select"]);

const { isSelected, toggleCompare } = useJobCompare();
const { isJobApplied } = useJobApplication();
const { isJobBooked } = useJobInterviewBooking();

const applied = computed(() => isJobApplied(props.job.job_id || props.job.id));
const booked = computed(() => isJobBooked(props.job.job_id || props.job.id));

const compareSelected = computed(() => isSelected(props.job.job_id || props.job.id));

const title = computed(() => props.job.job_title || props.job.job_name || "-");
const company = computed(
  () => props.job.company_name || props.job.company_relation?.company_name || "-"
);
const city = computed(() => props.job.city || "-");
const salary = computed(() => props.job.salary_range_month || props.job.salary || "面议");
const score = computed(() => {
  const s = props.job.score;
  if (s == null || s === "") return null;
  return Math.round(Number(s));
});

const matchTags = computed(() => {
  const tags = [];
  const s = score.value;
  if (s != null && s >= 80) tags.push({ label: "学历匹配", tone: "purple" });
  if (props.job.job_category || s >= 75) tags.push({ label: "专业匹配", tone: "orange" });
  if (props.job.city) tags.push({ label: "地区匹配", tone: "blue" });
  if (props.job.salary_range_month || s >= 70) tags.push({ label: "薪资匹配", tone: "green" });
  return tags.slice(0, 4);
});

const requirements = computed(() => {
  const cat = props.job.job_category;
  return cat ? `经验不限 | ${cat}` : "经验不限 | 本科";
});

function onCardClick() {
  emit("select", props.job);
}
</script>

<template>
  <article
    class="job-card"
    :class="{
      'job-card--active': active,
      'job-card--hover': hover && !active,
      'job-card--pinned': pinned
    }"
    :aria-selected="active"
    tabindex="0"
    @mouseenter="emit('hover', job)"
    @click="onCardClick"
    @keydown.enter.prevent="onCardClick"
  >
    <button
      type="button"
      class="compare-toggle"
      :class="{ 'compare-toggle--on': compareSelected }"
      :aria-label="compareSelected ? '取消对比' : '加入对比'"
      :title="compareSelected ? '取消对比' : '加入对比（最多3个）'"
      @click.stop="toggleCompare(job.job_id || job.id)"
    >
      <span v-if="compareSelected" class="compare-check">✓</span>
      <span v-else class="compare-plus">+</span>
    </button>

    <span v-if="pinned" class="pin-badge">已固定</span>

    <header class="job-card-head">
      <div class="job-card-head-main">
        <h3 class="job-title">{{ title }}</h3>
        <JobIdTag
          :job-id="job.job_id || job.id"
          class="job-card-id-tag"
          @click.stop
        />
      </div>
      <div v-if="score != null" class="match-score">{{ score }}%</div>
    </header>

    <p class="job-meta">{{ company }} · {{ city }}</p>

    <div class="match-tags">
      <span v-for="tag in matchTags" :key="tag.label" class="match-tag" :class="'match-tag--' + tag.tone">
        {{ tag.label }}
      </span>
    </div>

    <div class="job-foot">
      <span class="job-req">{{ requirements }}</span>
      <span class="job-salary">{{ salary }}</span>
    </div>

    <div class="job-actions" @click.stop>
      <button type="button" class="action-btn" @click="emit('view-detail', job)">查看详情</button>
      <button
        type="button"
        class="action-btn action-btn--primary"
        :class="{ 'action-btn--applied': applied }"
        :disabled="applied"
        @click="emit('apply', job)"
      >
        {{ applied ? "已投递" : "一键投递" }}
      </button>
      <button type="button" class="action-btn" @click="emit('resume', job)">生成简历</button>
      <button
        type="button"
        class="action-btn"
        :class="{ 'action-btn--booked': booked }"
        :disabled="booked"
        @click="emit('interview', job)"
      >
        {{ booked ? "已预约" : "预约面试" }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.job-card {
  position: relative;
  background: #fff;
  border: 1px solid rgba(91, 106, 223, 0.1);
  border-radius: 14px;
  padding: 14px 14px 12px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  height: auto;
  align-self: start;
  cursor: pointer;
  overflow: visible;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s, transform 0.18s;
}
.job-card:focus {
  outline: 2px solid #a5b4fc;
  outline-offset: 2px;
}
.job-card--hover {
  border-color: #c7d2fe;
  background: #f8fafc;
  transform: translateY(-1px);
}
.job-card--active {
  border-color: #a5b4fc;
  background: #eef2ff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.14);
}
.job-card--pinned {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.22);
}
.pin-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #6366f1;
  color: #fff;
  font-size: 0.58rem;
  font-weight: 700;
  line-height: 1.4;
  pointer-events: none;
}
.job-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.job-card-head-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.job-card-id-tag {
  z-index: 2;
}
.job-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  width: 100%;
}
.match-score {
  flex-shrink: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #16a34a;
  line-height: 1;
}
.job-meta {
  margin: 0 0 8px;
  font-size: 0.76rem;
  color: #64748b;
}
.match-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.match-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.68rem;
  font-weight: 600;
}
.match-tag--blue {
  background: #eff6ff;
  color: #2563eb;
}
.match-tag--green {
  background: #ecfdf5;
  color: #059669;
}
.match-tag--purple {
  background: #f5f3ff;
  color: #7c3aed;
}
.match-tag--orange {
  background: #fff7ed;
  color: #ea580c;
}
.job-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 0.72rem;
}
.job-req {
  color: #94a3b8;
}
.job-salary {
  color: #ea580c;
  font-weight: 700;
  font-size: 0.82rem;
}
.job-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px;
}
.action-btn {
  padding: 6px 4px;
  border-radius: 7px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.action-btn:hover {
  border-color: #a5b4fc;
  background: #f8fafc;
}
.action-btn--primary {
  background: #5b6adf;
  border-color: #5b6adf;
  color: #fff;
}
.action-btn--primary:hover {
  background: #4f46e5;
  border-color: #4f46e5;
}
.action-btn--applied,
.action-btn--applied:disabled,
.action-btn--booked,
.action-btn--booked:disabled {
  background: #e2e8f0;
  border-color: #cbd5e1;
  color: #64748b;
  cursor: default;
}
@media (min-width: 1100px) {
  .job-actions {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .action-btn {
    font-size: 0.64rem;
    padding: 6px 2px;
  }
}
.compare-toggle {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1.5px solid #d1d5db;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  color: #9ca3af;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.compare-toggle:hover {
  border-color: #6366f1;
  color: #6366f1;
}
.compare-toggle--on {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
}
.compare-check {
  font-size: 12px;
  line-height: 1;
}
.compare-plus {
  font-size: 16px;
  line-height: 1;
}
</style>
