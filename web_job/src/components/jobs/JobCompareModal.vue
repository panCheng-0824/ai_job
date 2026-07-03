<script setup>
import { computed, onBeforeUnmount, watch } from "vue";
import JobIdTag from "./JobIdTag.vue";
import {
  buildDimensionCompareRows,
  findBestCellIndices,
  resolveJobCompareView,
  scoreTone
} from "../../utils/jobCompareDisplay";

const props = defineProps({
  open: { type: Boolean, default: false },
  jobs: { type: Array, default: () => [] }
});

const emit = defineEmits(["close", "remove"]);

const columns = computed(() => props.jobs.slice(0, 3).map(resolveJobCompareView));

const bestScoreIndices = computed(() =>
  findBestCellIndices(columns.value.map((c) => ({ score: c.score, hasData: c.score != null })))
);

const basicRows = computed(() => {
  const cols = columns.value;
  if (!cols.length) return [];
  return [
    { key: "company", label: "公司", pick: (j) => j.company },
    { key: "city", label: "城市", pick: (j) => j.city },
    { key: "salary", label: "薪资", pick: (j) => j.salary },
    { key: "category", label: "岗位类别", pick: (j) => j.category },
    { key: "edu", label: "学历要求", pick: (j) => j.edu },
    { key: "exp", label: "经验要求", pick: (j) => j.exp }
  ].map((row) => ({
    key: row.key,
    label: row.label,
    values: cols.map(row.pick)
  }));
});

const dimensionRows = computed(() =>
  buildDimensionCompareRows(columns.value).map((row) => ({
    ...row,
    bestIndices: findBestCellIndices(row.cells)
  }))
);

const hasDimensionScores = computed(() =>
  dimensionRows.value.some((row) => row.cells.some((cell) => cell.hasData))
);

const dimensionTotalByCol = computed(() =>
  columns.value.map((col) => {
    const dims = col.dimensions?.filter((d) => d.score != null) || [];
    if (!dims.length) return null;
    return dims.reduce((sum, d) => sum + d.score, 0);
  })
);

function onKeydown(e) {
  if (e.key === "Escape") emit("close");
}

watch(
  () => props.open,
  (open) => {
    if (typeof document === "undefined") return;
    if (open) {
      document.addEventListener("keydown", onKeydown);
      document.body.style.overflow = "hidden";
    } else {
      document.removeEventListener("keydown", onKeydown);
      document.body.style.overflow = "";
    }
  }
);

onBeforeUnmount(() => {
  if (typeof document === "undefined") return;
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});

function removeJob(jobId) {
  emit("remove", jobId);
}

function toneClass(score) {
  return `compare-score-pill--${scoreTone(score)}`;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="compare-overlay" role="dialog" aria-modal="true" aria-label="岗位多维度对比" @click.self="$emit('close')">
        <div class="compare-modal">
          <header class="compare-modal-head">
            <div>
              <h2>岗位多维度对比</h2>
              <p class="compare-modal-sub">并排查看基础信息与五维匹配得分，最优项已高亮</p>
            </div>
            <button type="button" class="compare-modal-close" @click="$emit('close')">关闭</button>
          </header>

          <div v-if="!columns.length" class="compare-empty">
            <p>未找到已选岗位</p>
            <p class="compare-empty-hint">请先在卡片右上角勾选岗位（最多 3 个），再点击「开始对比」。</p>
          </div>

          <template v-else>
            <section class="compare-summary" :style="{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }">
              <article
                v-for="(col, idx) in columns"
                :key="col.jobId"
                class="compare-summary-card"
                :class="{ 'compare-summary-card--best': bestScoreIndices.has(idx) }"
              >
                <div class="compare-summary-top">
                  <div class="compare-summary-title-wrap">
                    <h3 class="compare-summary-title">{{ col.title }}</h3>
                    <JobIdTag :job-id="col.jobId" size="compact" @click.stop />
                  </div>
                  <button
                    type="button"
                    class="compare-remove-btn"
                    title="移出对比"
                    @click="removeJob(col.jobId)"
                  >
                    ×
                  </button>
                </div>
                <p class="compare-summary-meta">{{ col.company }} · {{ col.city }}</p>
                <div class="compare-summary-foot">
                  <span v-if="col.score != null" class="compare-score-pill" :class="toneClass(col.score)">
                    综合 {{ col.score }}
                    <span v-if="bestScoreIndices.has(idx)" class="compare-best-tag">最优</span>
                  </span>
                  <span v-else class="compare-score-pill compare-score-pill--muted">暂无综合分</span>
                  <span class="compare-salary">{{ col.salary }}</span>
                </div>
              </article>
            </section>

            <div class="compare-table-wrap">
              <table class="compare-table">
                <thead>
                  <tr>
                    <th class="compare-th compare-th--label sticky-col">对比项</th>
                    <th v-for="col in columns" :key="`head-${col.jobId}`" class="compare-th">
                      {{ col.title }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="compare-section-row">
                    <th class="sticky-col" :colspan="columns.length + 1">基础信息</th>
                  </tr>
                  <tr v-for="row in basicRows" :key="row.key">
                    <th class="compare-row-label sticky-col">{{ row.label }}</th>
                    <td v-for="(value, idx) in row.values" :key="`${row.key}-${idx}`" class="compare-cell">
                      {{ value }}
                    </td>
                  </tr>

                  <tr class="compare-section-row">
                    <th class="sticky-col" :colspan="columns.length + 1">五维匹配得分</th>
                  </tr>

                  <template v-if="hasDimensionScores">
                    <tr v-for="row in dimensionRows" :key="row.key">
                      <th class="compare-row-label sticky-col">
                        <span class="compare-dim-label">{{ row.label }}</span>
                        <span v-if="row.desc" class="compare-dim-desc">{{ row.desc }}</span>
                      </th>
                      <td
                        v-for="(cell, idx) in row.cells"
                        :key="`${row.key}-${idx}`"
                        class="compare-cell"
                        :class="{ 'compare-cell--best': row.bestIndices.has(idx) }"
                      >
                        <template v-if="cell.hasData">
                          <div class="compare-dim-score">
                            <span class="compare-dim-text">{{ cell.text }}</span>
                            <span v-if="row.bestIndices.has(idx)" class="compare-cell-best">优</span>
                          </div>
                          <div class="compare-progress" aria-hidden="true">
                            <span class="compare-progress-fill" :style="{ width: `${Math.round(cell.ratio * 100)}%` }" />
                          </div>
                        </template>
                        <span v-else class="compare-cell-empty">-</span>
                      </td>
                    </tr>
                    <tr>
                      <th class="compare-row-label sticky-col">维度合计</th>
                      <td
                        v-for="(total, idx) in dimensionTotalByCol"
                        :key="`total-${idx}`"
                        class="compare-cell compare-cell--total"
                      >
                        {{ total != null ? total : "-" }}
                      </td>
                    </tr>
                  </template>
                  <tr v-else>
                    <th class="compare-row-label sticky-col">评分明细</th>
                    <td :colspan="columns.length" class="compare-cell compare-cell--muted">
                      暂无五维得分。请完成智能匹配，并确保推荐理由包含【评分依据】段落（格式：维度名 X/Y 分）。
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.compare-overlay {
  position: fixed;
  inset: 0;
  z-index: 14000;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(2px);
}
.compare-modal {
  width: min(96vw, 1120px);
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.22);
}
.compare-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.compare-modal-head h2 {
  margin: 0;
  font-size: 1.08rem;
  font-weight: 700;
  color: #0f172a;
}
.compare-modal-sub {
  margin: 4px 0 0;
  font-size: 0.76rem;
  color: #64748b;
  line-height: 1.45;
}
.compare-modal-close {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  border-radius: 10px;
  padding: 7px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}
.compare-modal-close:hover {
  background: #f8fafc;
}
.compare-empty {
  padding: 36px 24px;
  text-align: center;
  color: #64748b;
}
.compare-empty p {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
}
.compare-empty-hint {
  margin-top: 8px !important;
  font-size: 0.8rem !important;
  font-weight: 400 !important;
  line-height: 1.55;
  color: #94a3b8;
}

.compare-summary {
  display: grid;
  gap: 1px;
  background: #e2e8f0;
  flex-shrink: 0;
}
.compare-summary-card {
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
  padding: 14px 16px;
  border-bottom: 1px solid #eef2ff;
}
.compare-summary-card--best {
  background: linear-gradient(180deg, #eef2ff 0%, #fff 100%);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.18);
}
.compare-summary-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.compare-summary-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.compare-summary-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.compare-summary-meta {
  margin: 6px 0 10px;
  font-size: 0.76rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.compare-summary-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.compare-score-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}
.compare-score-pill--excellent {
  background: #ecfdf5;
  color: #047857;
}
.compare-score-pill--good {
  background: #eef2ff;
  color: #4338ca;
}
.compare-score-pill--fair {
  background: #fff7ed;
  color: #c2410c;
}
.compare-score-pill--low {
  background: #fef2f2;
  color: #b91c1c;
}
.compare-score-pill--muted {
  background: #f1f5f9;
  color: #94a3b8;
  font-weight: 600;
}
.compare-best-tag {
  padding: 1px 6px;
  border-radius: 999px;
  background: #4338ca;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 700;
}
.compare-salary {
  font-size: 0.78rem;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}
.compare-remove-btn {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #94a3b8;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.compare-remove-btn:hover {
  color: #ef4444;
  border-color: #fecaca;
  background: #fef2f2;
}

.compare-table-wrap {
  overflow: auto;
  flex: 1;
  min-height: 0;
}
.compare-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 640px;
}
.compare-th,
.compare-row-label,
.compare-cell {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.84rem;
  vertical-align: top;
  text-align: left;
}
.compare-th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f8fafc;
  color: #0f172a;
  font-weight: 700;
  box-shadow: 0 1px 0 #e2e8f0;
}
.compare-th--label,
.compare-row-label.sticky-col {
  position: sticky;
  left: 0;
  z-index: 3;
  width: 132px;
  min-width: 132px;
  background: #fafbff;
  box-shadow: 1px 0 0 #f1f5f9;
}
.compare-th--label {
  z-index: 4;
  color: #64748b;
}
.compare-row-label {
  color: #64748b;
  font-weight: 600;
}
.compare-dim-label {
  display: block;
  color: #334155;
}
.compare-dim-desc {
  display: block;
  margin-top: 2px;
  font-size: 0.68rem;
  font-weight: 400;
  color: #94a3b8;
  line-height: 1.4;
}
.compare-cell {
  color: #334155;
  min-width: 168px;
}
.compare-cell--best {
  background: #f5f7ff;
}
.compare-cell--total {
  font-weight: 700;
  color: #4338ca;
}
.compare-cell--muted {
  color: #94a3b8;
  line-height: 1.55;
}
.compare-cell-empty {
  color: #cbd5e1;
}
.compare-dim-score {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.compare-dim-text {
  font-weight: 700;
  color: #1e293b;
}
.compare-cell-best {
  padding: 1px 5px;
  border-radius: 4px;
  background: #4338ca;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 700;
}
.compare-progress {
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}
.compare-progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #818cf8, #6366f1);
  transition: width 0.35s ease;
}
.compare-section-row th {
  padding: 10px 14px 8px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  border-bottom: 1px solid #e0e7ff;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-active .compare-modal,
.modal-fade-leave-active .compare-modal {
  transition: transform 0.22s ease, opacity 0.22s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .compare-modal,
.modal-fade-leave-to .compare-modal {
  transform: translateY(12px) scale(0.98);
  opacity: 0;
}

@media (max-width: 720px) {
  .compare-overlay {
    padding: 0;
    align-items: flex-end;
  }
  .compare-modal {
    width: 100%;
    max-height: 92vh;
    border-radius: 18px 18px 0 0;
  }
  .compare-summary {
    grid-template-columns: 1fr !important;
  }
}
</style>
