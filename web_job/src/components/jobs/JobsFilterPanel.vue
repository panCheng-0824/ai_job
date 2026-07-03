<script setup>
/**
 * 岗位中心左侧筛选栏（对齐设计稿）。
 */
import { ref } from "vue";
import { useIsMobile } from "../../composables/useIsMobile";

const props = defineProps({
  cities: { type: Array, default: () => [] },
  provinces: { type: Array, default: () => [] },
  companyTypes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  /** 嵌入父级抽屉时始终展示表单，不启用组件内移动端底部弹层 */
  embedded: { type: Boolean, default: false }
});

const emit = defineEmits(["apply", "reset"]);

const province = defineModel("province", { type: String, default: "" });
const city = defineModel("city", { type: String, default: "" });
const salaryMin = defineModel("salaryMin", { type: String, default: "" });
const salaryMax = defineModel("salaryMax", { type: String, default: "" });
const education = defineModel("education", { type: Array, default: () => [] });
const companySize = defineModel("companySize", { type: Array, default: () => [] });
const jobNature = defineModel("jobNature", { type: Array, default: () => [] });
const publishTime = defineModel("publishTime", { type: String, default: "" });
const selectedCompanyType = defineModel("selectedCompanyType", { type: String, default: "" });

const { isMobile } = useIsMobile();
const mobileFilterOpen = ref(false);

const educationOptions = [
  { value: "bachelor", label: "本科及以上" },
  { value: "master", label: "硕士及以上" },
  { value: "doctor", label: "博士" },
  { value: "any", label: "不限" }
];

const companySizeOptions = [
  { value: "500", label: "世界500强" },
  { value: "1000+", label: "1000人以上" },
  { value: "500-1000", label: "500-1000人" },
  { value: "<100", label: "100人以下" }
];

const jobNatureOptions = [
  { value: "full", label: "全职" },
  { value: "intern", label: "实习" },
  { value: "campus", label: "校招" },
  { value: "social", label: "社招" }
];

const publishOptions = [
  { value: "3d", label: "近3天" },
  { value: "7d", label: "近7天" },
  { value: "30d", label: "近1月" },
  { value: "", label: "不限" }
];

function toggleArrayValue(list, value) {
  const arr = [...(list || [])];
  const idx = arr.indexOf(value);
  if (idx >= 0) arr.splice(idx, 1);
  else arr.push(value);
  return arr;
}

function onEducationChange(value) {
  education.value = toggleArrayValue(education.value, value);
}

function onCompanySizeChange(value) {
  companySize.value = toggleArrayValue(companySize.value, value);
}

function onJobNatureChange(value) {
  jobNature.value = toggleArrayValue(jobNature.value, value);
}

function onPublishChange(value) {
  publishTime.value = publishTime.value === value ? "" : value;
}
</script>

<template>
  <button
    v-if="isMobile && !embedded"
    type="button"
    class="mobile-filter-btn"
    @click="mobileFilterOpen = !mobileFilterOpen"
  >
    筛选 {{ mobileFilterOpen ? '▲' : '▼' }}
  </button>
  <Transition name="sheet-slide">
    <div v-if="isMobile && !embedded && mobileFilterOpen" class="mobile-filter-backdrop" @click="mobileFilterOpen = false" />
  </Transition>
  <Transition name="sheet-slide">
    <aside
      v-if="embedded || !isMobile || mobileFilterOpen"
      class="jobs-filter"
      :class="{
        'jobs-filter--disabled': disabled,
        'jobs-filter--sheet': isMobile && !embedded,
        'jobs-filter--embedded': embedded
      }"
      aria-label="职位筛选"
    >
    <header class="jobs-filter-head">
      <h2 class="jobs-filter-title">职位筛选</h2>
      <p v-if="disabled" class="filter-disabled-hint">当前为「热门企业」视图，请使用顶部搜索框检索企业</p>
    </header>

    <div class="jobs-filter-scroll">
    <section class="filter-block">
      <h3>工作地点</h3>
      <div class="filter-row">
        <select v-model="province" class="filter-input" aria-label="省份">
          <option value="">全部省份</option>
          <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-model="city" class="filter-input" aria-label="城市">
          <option value="">全部城市</option>
          <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </section>

    <section class="filter-block">
      <h3>薪资范围</h3>
      <div class="salary-row">
        <input v-model="salaryMin" type="number" min="0" class="filter-input" placeholder="最低" />
        <span class="salary-sep">-</span>
        <input v-model="salaryMax" type="number" min="0" class="filter-input" placeholder="最高" />
        <span class="salary-unit">K</span>
      </div>
    </section>

    <section class="filter-block">
      <h3>学历要求</h3>
      <div class="check-grid">
        <label v-for="opt in educationOptions" :key="opt.value" class="check-item">
          <input
            type="checkbox"
            :checked="education.includes(opt.value)"
            @change="onEducationChange(opt.value)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </section>

    <section class="filter-block">
      <h3>公司规模</h3>
      <div class="check-grid">
        <label v-for="opt in companySizeOptions" :key="opt.value" class="check-item">
          <input
            type="checkbox"
            :checked="companySize.includes(opt.value)"
            @change="onCompanySizeChange(opt.value)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </section>

    <section class="filter-block">
      <h3>工作性质</h3>
      <div class="check-grid">
        <label v-for="opt in jobNatureOptions" :key="opt.value" class="check-item">
          <input
            type="checkbox"
            :checked="jobNature.includes(opt.value)"
            @change="onJobNatureChange(opt.value)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </section>

    <section class="filter-block">
      <h3>发布时间</h3>
      <div class="check-grid">
        <label v-for="opt in publishOptions" :key="opt.value || 'any'" class="check-item">
          <input
            type="checkbox"
            :checked="publishTime === opt.value"
            @change="onPublishChange(opt.value)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </section>

    <section v-if="companyTypes.length" class="filter-block">
      <h3>单位性质</h3>
      <div class="chip-list">
        <button
          type="button"
          class="chip-btn"
          :class="{ active: !selectedCompanyType }"
          @click="selectedCompanyType = ''"
        >
          全部
        </button>
        <button
          v-for="item in companyTypes"
          :key="item.code"
          type="button"
          class="chip-btn"
          :class="{ active: selectedCompanyType === item.code }"
          @click="selectedCompanyType = selectedCompanyType === item.code ? '' : item.code"
        >
          {{ item.label }}
        </button>
      </div>
    </section>
    </div>

    <div class="filter-actions" :class="{ 'filter-actions--embedded': embedded }">
      <button type="button" class="btn-reset" :disabled="disabled || loading" @click="emit('reset')">重置</button>
      <button type="button" class="btn-apply" :disabled="disabled || loading" @click="emit('apply')">应用</button>
    </div>
  </aside>
  </Transition>
</template>

<style scoped>
.jobs-filter {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border);
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px 14px;
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  max-height: calc(100vh - var(--home-topbar-h, 56px) - 32px);
  overflow: auto;
}
.jobs-filter--embedded {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  max-height: none;
  position: static;
  top: auto;
  overflow: hidden;
  padding: 0;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}
.jobs-filter-head {
  flex-shrink: 0;
}
.jobs-filter--embedded .jobs-filter-title {
  margin-bottom: 10px;
}
.jobs-filter-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding-right: 4px;
}
.jobs-filter:not(.jobs-filter--embedded) .jobs-filter-scroll {
  flex: none;
  overflow: visible;
  padding-right: 0;
}
.filter-actions--embedded {
  flex-shrink: 0;
  margin-top: 0;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #fff 14px);
}
.jobs-filter-title {
  margin: 0 0 14px;
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
}
.filter-block {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.filter-block:last-of-type {
  border-bottom: none;
}
.filter-block h3 {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}
.filter-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.filter-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 7px 8px;
  font-size: 0.76rem;
  color: #334155;
  background: #fff;
}
.salary-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto;
  gap: 6px;
  align-items: center;
}
.salary-sep,
.salary-unit {
  font-size: 0.76rem;
  color: #94a3b8;
}
.check-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 8px;
}
.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.74rem;
  color: #475569;
  cursor: pointer;
}
.check-item input {
  accent-color: #5b6adf;
}
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip-btn {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 10px;
  background: #fff;
  color: #475569;
  font-size: 0.72rem;
  cursor: pointer;
}
.chip-btn.active {
  border-color: #818cf8;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 600;
}
.filter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}
.btn-reset,
.btn-apply {
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-reset {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
}
.btn-apply {
  border: none;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
}
.btn-apply:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.jobs-filter--disabled {
  opacity: 0.72;
}
.jobs-filter--disabled .filter-block {
  pointer-events: none;
}
.filter-disabled-hint {
  margin: -6px 0 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.72rem;
  line-height: 1.45;
}
.mobile-filter-btn {
  display: block;
  width: 100%;
  padding: 10px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #475569;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
}
.mobile-filter-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1080;
  background: rgba(15, 23, 42, 0.4);
}
.jobs-filter--sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1085;
  max-height: 70vh;
  overflow-y: auto;
  border-radius: 16px 16px 0 0;
  background: #fff;
  padding: 16px;
  box-shadow: 0 -4px 20px rgba(15, 23, 42, 0.12);
}
.sheet-slide-enter-active,
.sheet-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.sheet-slide-enter-from,
.sheet-slide-leave-to {
  opacity: 0;
}
.jobs-filter--sheet.sheet-slide-enter-from,
.jobs-filter--sheet.sheet-slide-leave-to {
  transform: translateY(20%);
}
</style>
