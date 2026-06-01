<script setup>
/**
 * 模拟面试官规划预览操作条。
 * 按 plan_id + chat_session_id 查库：有记录显示「进入」，否则显示「开始」。
 */
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { lookupInterviewRecordByPlanAndChat, startInterviewFromPlan } from "../../modules/interview/api";

const props = defineProps({
  planId: { type: String, required: true },
  planVersion: { type: Number, default: null },
  studentId: { type: String, required: true },
  chatSessionId: { type: String, default: "" },
  disabled: { type: Boolean, default: false }
});

const emit = defineEmits(["started", "enter", "error"]);

const router = useRouter();
const checking = ref(false);
const loading = ref(false);
const done = ref(false);
const hint = ref("");
const recordId = ref("");
const interviewSessionId = ref("");
const ctxKey = ref("");

function resetToStart() {
  done.value = false;
  recordId.value = "";
  interviewSessionId.value = "";
  ctxKey.value = "";
  hint.value = "";
}

function applyLookupResult(data) {
  if (data?.exists && data.record_id) {
    done.value = true;
    recordId.value = String(data.record_id);
    interviewSessionId.value = String(data.interview_session_id || "");
    hint.value = "已有关联面试记录，点击「进入」继续面试。";
  } else {
    resetToStart();
  }
}

/** 按 plan_id + chat_session_id 精确查询是否已创建记录 */
async function refreshRecordState() {
  const sid = String(props.studentId || "").trim();
  const pid = String(props.planId || "").trim();
  const cs = String(props.chatSessionId || "").trim();
  if (!sid || !pid || !cs) {
    resetToStart();
    return;
  }
  checking.value = true;
  try {
    const resp = await lookupInterviewRecordByPlanAndChat(sid, pid, cs);
    applyLookupResult(resp);
  } catch {
    resetToStart();
  } finally {
    checking.value = false;
  }
}

onMounted(() => {
  void refreshRecordState();
});

watch(
  () => [props.planId, props.chatSessionId, props.studentId],
  () => {
    void refreshRecordState();
  }
);

async function onStart() {
  if (loading.value || checking.value || done.value || props.disabled || !props.planId) return;
  const cs = String(props.chatSessionId || "").trim();
  if (!cs) {
    hint.value = "请先进入聊天会话后再开始面试";
    return;
  }
  loading.value = true;
  hint.value = "";
  try {
    const data = await startInterviewFromPlan({
      student_id: props.studentId,
      plan_id: props.planId,
      plan_version: props.planVersion,
      chat_session_id: cs
    });
    done.value = true;
    recordId.value = String(data?.record_id || "");
    interviewSessionId.value = String(data?.interview_session_id || "");
    ctxKey.value = String(data?.ctx_key || "");
    hint.value = "面试记录已创建，点击「进入」开始遮层面试。";
    emit("started", data);
  } catch (e) {
    const msg = e?.message || "创建面试失败";
    hint.value = msg;
    emit("error", msg);
  } finally {
    loading.value = false;
  }
}

function onEnter() {
  if (!recordId.value) {
    router.push({ path: "/me", query: { tab: "interviews" } });
    return;
  }
  emit("enter", {
    record_id: recordId.value,
    interview_session_id: interviewSessionId.value,
    plan_id: props.planId,
    plan_version: props.planVersion,
    chat_session_id: props.chatSessionId,
    student_id: props.studentId,
    ctx_key: ctxKey.value
  });
}

function onPrimaryClick() {
  if (done.value) onEnter();
  else onStart();
}

const buttonLabel = () => {
  if (checking.value) return "加载中…";
  if (loading.value) return "创建中…";
  if (done.value) return "进入";
  return "开始";
};
</script>

<template>
  <div class="plan-start-bar" role="group" :aria-label="done ? '进入面试记录' : '开始正式面试'">
    <button
      type="button"
      class="plan-start-btn"
      :class="{ 'plan-start-btn--enter': done }"
      :disabled="disabled || loading || !planId || (checking && !done)"
      @click="onPrimaryClick"
    >
      {{ buttonLabel() }}
    </button>
    <p v-if="hint" class="plan-start-hint" :class="{ 'plan-start-hint--err': !done && hint && !loading && !checking }">
      {{ hint }}
    </p>
  </div>
</template>

<style scoped>
.plan-start-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-soft, #e2e8f0);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.plan-start-btn {
  padding: 6px 18px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.plan-start-btn--enter {
  background: linear-gradient(135deg, #059669, #047857);
}
.plan-start-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.plan-start-hint {
  flex: 1 1 100%;
  margin: 0;
  font-size: 12px;
  color: var(--text-muted, #64748b);
}
.plan-start-hint--err {
  color: #b91c1c;
}
</style>
