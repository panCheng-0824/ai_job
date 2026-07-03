<script setup>
/**
 * 视频面试房间页：加载记录详情并进入房间壳层。
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, getStudentId } from "../api/client";
import InterviewVideoRoomShell from "../components/interview/InterviewVideoRoomShell.vue";
import { useHomePageHeader } from "../composables/useHomePageHeader";
import { useInterviewRecordDetail } from "../modules/interview/useInterviewRecordDetail";

const route = useRoute();
const router = useRouter();
const studentName = ref("");

const recordIdRef = computed(() => route.params.recordId);
const { detail, loadError, loading } = useInterviewRecordDetail(recordIdRef);

async function loadStudentName() {
  const studentId = getStudentId();
  if (!studentId) return;
  try {
    const resp = await apiGet(`/api/students/${encodeURIComponent(studentId)}`);
    studentName.value = resp?.学生基本信息?.姓名 || "";
  } catch {
    studentName.value = "";
  }
}

function onExit() {
  router.push("/interview/center");
}

watch(
  () => route.params.recordId,
  () => {
    loadStudentName();
  },
  { immediate: true }
);

useHomePageHeader(
  computed(() => ({
    title: "视频面试",
    subtitle: "模拟面试房间 · 准备好后点击开始答题",
    studentName: studentName.value
  }))
);
</script>

<template>
  <div class="home-main room-page-main">
    <p v-if="!getStudentId()" class="state warn">
      请先
      <router-link to="/login">登录</router-link>
      后进入面试房间。
    </p>
    <p v-else-if="loadError" class="state error">{{ loadError }}</p>
    <p v-else-if="loading && !detail" class="state muted">加载面试信息…</p>
    <InterviewVideoRoomShell
      v-else-if="detail"
      :record="detail"
      :student-name="studentName"
      @exit="onExit"
    />
  </div>
</template>

<style scoped>
.room-page-main {
  min-height: calc(100vh - var(--home-topbar-h, 56px));
}

.state {
  margin: 24px 0;
  text-align: center;
  font-size: 0.9rem;
}

.state.warn {
  color: #b45309;
}

.state.error {
  color: #dc2626;
  font-weight: 600;
}

.state.muted {
  color: #64748b;
}

.state a {
  color: var(--home-primary, #5b6adf);
  font-weight: 600;
}
</style>
