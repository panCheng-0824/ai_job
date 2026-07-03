<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
});

const form = reactive({
  targetRoles: "",
  targetCities: "",
  targetCompanies: "",
  salaryMin: "",
  salaryMax: "",
  salaryNegotiable: true,
  queryText: ""
});

const CITY_PRESETS = ["上海", "北京", "深圳", "杭州", "广州", "成都"];
const ROLE_PRESETS = ["Java开发", "前端开发", "产品经理", "数据分析"];

function linesToArray(text) {
  return String(text || "")
    .split(/[,，、\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function arrayToLines(arr) {
  return Array.isArray(arr) ? arr.join("、") : "";
}

function appendToken(field, token) {
  const current = linesToArray(form[field]);
  if (current.includes(token)) return;
  current.push(token);
  form[field] = current.join("、");
}

watch(
  () => props.modelValue,
  (v) => {
    form.targetRoles = arrayToLines(v?.targetRoles);
    form.targetCities = arrayToLines(v?.targetCities);
    form.targetCompanies = arrayToLines(v?.targetCompanies);
    form.salaryMin = v?.salaryMin != null ? String(v.salaryMin) : "";
    form.salaryMax = v?.salaryMax != null ? String(v.salaryMax) : "";
    form.salaryNegotiable = v?.salaryNegotiable !== false;
    form.queryText = v?.queryText || "";
  },
  { immediate: true, deep: true }
);

function parseSalary(raw) {
  const t = String(raw || "").trim();
  if (!t) return null;
  const n = Number.parseInt(t, 10);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function getPayload() {
  return {
    targetRoles: linesToArray(form.targetRoles),
    targetCities: linesToArray(form.targetCities),
    targetCompanies: linesToArray(form.targetCompanies),
    salaryMin: form.salaryNegotiable ? null : parseSalary(form.salaryMin),
    salaryMax: form.salaryNegotiable ? null : parseSalary(form.salaryMax),
    salaryNegotiable: form.salaryNegotiable,
    queryText: form.queryText.trim()
  };
}

defineExpose({ getPayload });
</script>

<template>
  <div class="form-stack">
    <section class="form-section">
      <h4 class="form-section-title">意向信息</h4>
      <label class="field">
        <span>意向岗位</span>
        <input v-model="form.targetRoles" placeholder="多个用顿号或逗号分隔" />
        <div class="preset-row">
          <button
            v-for="item in ROLE_PRESETS"
            :key="item"
            type="button"
            class="preset-chip"
            @click="appendToken('targetRoles', item)"
          >
            + {{ item }}
          </button>
        </div>
      </label>
      <label class="field">
        <span>意向城市</span>
        <input v-model="form.targetCities" placeholder="如 上海、杭州" />
        <div class="preset-row">
          <button
            v-for="city in CITY_PRESETS"
            :key="city"
            type="button"
            class="preset-chip"
            @click="appendToken('targetCities', city)"
          >
            + {{ city }}
          </button>
        </div>
      </label>
      <label class="field">
        <span>意向企业 <em class="optional">可选</em></span>
        <input v-model="form.targetCompanies" placeholder="多个用顿号分隔" />
      </label>
    </section>

    <section class="form-section">
      <h4 class="form-section-title">薪资期望</h4>
      <label class="toggle-field">
        <input v-model="form.salaryNegotiable" type="checkbox" class="toggle-input" />
        <span class="toggle-box" aria-hidden="true" />
        <span class="toggle-label">薪资面议</span>
      </label>
      <div v-if="!form.salaryNegotiable" class="salary-row">
        <label class="field">
          <span>期望下限（元/月）</span>
          <input v-model="form.salaryMin" type="number" min="0" step="500" placeholder="8000" />
        </label>
        <label class="field">
          <span>期望上限（元/月）</span>
          <input v-model="form.salaryMax" type="number" min="0" step="500" placeholder="12000" />
        </label>
      </div>
    </section>

    <section class="form-section">
      <h4 class="form-section-title">综合诉求</h4>
      <p class="form-section-desc">补充你对行业、工作节奏、成长空间等的偏好描述。</p>
      <label class="field">
        <span class="sr-only">综合诉求</span>
        <textarea
          v-model="form.queryText"
          rows="4"
          placeholder="描述你的求职偏好，如行业方向、工作节奏、成长诉求等"
        />
      </label>
    </section>
  </div>
</template>

<style scoped>
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-section-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
}

.form-section-desc {
  margin: -4px 0 0;
  font-size: 0.74rem;
  color: #94a3b8;
  line-height: 1.45;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 0.76rem;
  font-weight: 600;
  color: #475569;
}

.optional {
  font-style: normal;
  font-weight: 500;
  color: #94a3b8;
}

.field input,
.field textarea {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.88rem;
  color: #0f172a;
  font-family: inherit;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.field textarea {
  resize: vertical;
  min-height: 96px;
  line-height: 1.55;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.preset-chip {
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 0.7rem;
  color: #64748b;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.preset-chip:hover {
  border-color: #818cf8;
  color: #4338ca;
  background: #eef2ff;
}

.toggle-field {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-box {
  width: 18px;
  height: 18px;
  border: 2px solid #cbd5e1;
  border-radius: 5px;
  background: #fff;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}

.toggle-input:checked + .toggle-box {
  border-color: var(--home-primary, #5b6adf);
  background: var(--home-primary, #5b6adf);
}

.toggle-input:checked + .toggle-box::after {
  content: "";
  position: absolute;
  left: 4px;
  top: 1px;
  width: 5px;
  height: 9px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.toggle-input:focus-visible + .toggle-box {
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.25);
}

.toggle-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #334155;
}

.salary-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 480px) {
  .salary-row {
    grid-template-columns: 1fr;
  }
}
</style>
