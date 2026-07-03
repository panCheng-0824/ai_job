<script setup>
defineProps({
  pendingCount: { type: Number, default: 0 },
  finishedCount: { type: Number, default: 0 },
  passRate: { type: Number, default: null },
  loading: { type: Boolean, default: false },
  activeFilter: { type: String, default: "all" }
});

defineEmits(["filter"]);

function passRateText(rate) {
  if (rate == null) return "—";
  return `${rate}%`;
}
</script>

<template>
  <div class="stat-row">
    <button
      type="button"
      class="stat-card stat-card--pending"
      :class="{ active: activeFilter === 'pending' }"
      @click="$emit('filter', 'pending')"
    >
      <div class="stat-icon" aria-hidden="true">⏳</div>
      <div class="stat-body">
        <p class="stat-label">待面试</p>
        <strong class="stat-value">{{ loading ? "…" : pendingCount }}</strong>
      </div>
    </button>
    <button
      type="button"
      class="stat-card stat-card--done"
      :class="{ active: activeFilter === 'done' }"
      @click="$emit('filter', 'done')"
    >
      <div class="stat-icon" aria-hidden="true">✓</div>
      <div class="stat-body">
        <p class="stat-label">已面试</p>
        <strong class="stat-value">{{ loading ? "…" : finishedCount }}</strong>
      </div>
    </button>
    <button
      type="button"
      class="stat-card stat-card--rate"
      :class="{ active: activeFilter === 'all' }"
      @click="$emit('filter', 'all')"
    >
      <div class="stat-icon" aria-hidden="true">%</div>
      <div class="stat-body">
        <p class="stat-label">面试通过率</p>
        <strong class="stat-value">{{ loading ? "…" : passRateText(passRate) }}</strong>
      </div>
    </button>
  </div>
</template>

<style scoped>
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
  background: #fff;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition:
    border-color 0.18s,
    box-shadow 0.18s,
    transform 0.18s;
}

.stat-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(91, 106, 223, 0.12);
}

.stat-card.active {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.16);
}

.stat-card--pending {
  background: linear-gradient(135deg, #faf5ff 0%, #fff 55%);
}

.stat-card--done {
  background: linear-gradient(135deg, #ecfdf5 0%, #fff 55%);
}

.stat-card--rate {
  background: linear-gradient(135deg, #eff6ff 0%, #fff 55%);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.1rem;
  font-weight: 700;
  flex-shrink: 0;
}

.stat-card--pending .stat-icon {
  background: #ede9fe;
  color: #6d28d9;
}

.stat-card--done .stat-icon {
  background: #d1fae5;
  color: #047857;
}

.stat-card--rate .stat-icon {
  background: #dbeafe;
  color: #1d4ed8;
}

.stat-label {
  margin: 0 0 4px;
  font-size: 0.82rem;
  color: #64748b;
}

.stat-value {
  font-size: 1.65rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}

@media (max-width: 900px) {
  .stat-row {
    grid-template-columns: 1fr;
  }
}
</style>
