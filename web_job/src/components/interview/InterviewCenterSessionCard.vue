<script setup>
import { computed } from "vue";
import {
  formatRecordSchedule,
  historyStatusMeta,
  isJobBookingCard,
  recordCompanyLabel,
  recordDisplayTitle,
  upcomingStatusMeta
} from "../../modules/interview/recordCenterMeta";

const props = defineProps({
  item: { type: Object, required: true },
  variant: { type: String, default: "upcoming" },
  active: { type: Boolean, default: false }
});

const emit = defineEmits(["enter-room", "open-detail"]);

const title = computed(() => recordDisplayTitle(props.item));
const company = computed(() => recordCompanyLabel(props.item));
const schedule = computed(() => formatRecordSchedule(props.item.created_at));

const statusMeta = computed(() =>
  props.variant === "history"
    ? historyStatusMeta(props.item.session_status)
    : upcomingStatusMeta(props.item.session_status)
);

const isJobBooking = computed(() => isJobBookingCard(props.item));

const canEnterRoom = computed(
  () => props.variant === "upcoming" && Boolean(props.item.interview_session_id) && !isJobBooking.value
);

function onCardClick() {
  if (props.variant === "history") {
    emit("open-detail", props.item.record_id);
    return;
  }
  if (canEnterRoom.value) {
    emit("enter-room", props.item.record_id);
  } else {
    emit("open-detail", props.item.record_id);
  }
}

function onEnterRoom(e) {
  e.stopPropagation();
  emit("enter-room", props.item.record_id);
}

function onOpenDetail(e) {
  e.stopPropagation();
  emit("open-detail", props.item.record_id);
}
</script>

<template>
  <article
    class="session-card"
    :class="[
      `session-card--${variant}`,
      { 'session-card--active': active, 'session-card--clickable': true }
    ]"
    role="button"
    tabindex="0"
    @click="onCardClick"
    @keydown.enter="onCardClick"
    @keydown.space.prevent="onCardClick"
  >
    <header class="session-head">
      <h3 class="session-title">{{ title }}</h3>
      <span class="status-pill" :class="`status-pill--${statusMeta.tone}`">{{ statusMeta.label }}</span>
    </header>

    <ul class="session-meta">
      <li>
        <span class="meta-icon" aria-hidden="true">🕐</span>
        <span>{{ schedule }}</span>
      </li>
      <li>
        <span class="meta-icon" aria-hidden="true">👤</span>
        <span>AI 面试官</span>
      </li>
    </ul>

    <footer class="session-foot" @click.stop>
      <span class="company">{{ company }}</span>
      <div class="foot-actions">
        <button
          v-if="variant === 'upcoming' && canEnterRoom"
          type="button"
          class="btn btn-primary"
          @click="onEnterRoom"
        >
          进入房间
        </button>
        <button
          v-else-if="variant === 'upcoming' && isJobBooking"
          type="button"
          class="btn btn-primary"
          @click="onOpenDetail"
        >
          去准备
        </button>
        <button
          v-else-if="variant === 'upcoming'"
          type="button"
          class="btn btn-primary"
          @click="onOpenDetail"
        >
          查看详情
        </button>
        <button v-else type="button" class="btn btn-outline" @click="onOpenDetail">查看回放</button>
      </div>
    </footer>
  </article>
</template>

<style scoped>
.session-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: #fff;
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
  min-height: 168px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.session-card--clickable {
  cursor: pointer;
}

.session-card--clickable:hover {
  border-color: #c7d2fe;
  box-shadow: 0 10px 28px rgba(91, 106, 223, 0.14);
  transform: translateY(-2px);
}

.session-card--active {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
}

.session-card:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.session-card--history {
  min-height: 0;
  padding: 14px;
}

.session-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.session-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.45;
  word-break: break-word;
}

.status-pill {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
}

.status-pill--live {
  background: #dcfce7;
  color: #15803d;
}

.status-pill--pending {
  background: #ffedd5;
  color: #c2410c;
}

.status-pill--ended,
.status-pill--muted {
  background: #f1f5f9;
  color: #64748b;
}

.session-meta {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.session-meta li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #64748b;
}

.meta-icon {
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.session-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.company {
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.foot-actions {
  flex-shrink: 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
  cursor: pointer;
  font-family: inherit;
}

.btn-primary {
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.25);
}

.btn-outline {
  background: #fff;
  border-color: #c7d2fe;
  color: #4338ca;
}

.btn-outline:hover {
  background: #eef2ff;
}
</style>
