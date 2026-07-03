<script setup>
/**
 * 侧栏头像触发的「我的」浮层：从侧栏右侧弹出，展示账号概览与快捷入口。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { apiGet, getStudentId, isLoggedIn, logout } from "../../api/client";
import { setStudentServerAvatar } from "../../composables/useStudentAvatar";
import { uploadStudentAvatar } from "../../composables/useStudentProfile";
import StudentAvatar from "./StudentAvatar.vue";
import { maskName, maskOrgText, maskEducation, maskStudentField } from "../../utils/studentDesensitize";

const props = defineProps({
  open: { type: Boolean, default: false }
});

const emit = defineEmits(["update:open", "close"]);

const router = useRouter();

const loading = ref(false);
const loadError = ref("");
const summary = ref(null);
const studentInfo = ref({});

const studentId = computed(() => getStudentId());
const guest = computed(() => !studentId.value);
const studentName = computed(() => studentInfo.value["姓名"] || "同学");
const displayStudentName = computed(() => maskName(studentName.value) || "同学");
const displayStudentId = computed(() => maskStudentField("学号", studentId.value));
const avatarUrl = computed(() => studentInfo.value["头像"] || "");
const studentMajor = computed(() => {
  const parts = [
    maskOrgText(studentInfo.value["专业名称"]),
    studentInfo.value["毕业年度"] ? `${studentInfo.value["毕业年度"]}届` : "",
    maskEducation(studentInfo.value["学历"])
  ].filter(Boolean);
  return parts.join(" · ") || "完善学生画像";
});
/** 账号与数据入口；全局导航项不在此重复 */
const menuItems = [
  { key: "me", label: "个人中心", path: "/me", icon: "me" },
  { key: "fav", label: "我的收藏", path: "/me", query: { tab: "fav" }, icon: "fav" },
  { key: "fol", label: "我的关注", path: "/me", query: { tab: "fol" }, icon: "fol" }
];

const statItems = computed(() => {
  if (!summary.value) return [];
  return [
    { label: "收藏岗位", value: summary.value.favorite_job_count ?? 0 },
    { label: "关注企业", value: summary.value.followed_company_count ?? 0 },
    { label: "岗位评价", value: summary.value.job_review_count ?? 0 },
    { label: "企业评价", value: summary.value.company_review_count ?? 0 }
  ];
});

function close() {
  emit("update:open", false);
  emit("close");
}

async function loadPanelData() {
  const sid = studentId.value;
  if (!sid) {
    summary.value = null;
    studentInfo.value = {};
    return;
  }
  loading.value = true;
  loadError.value = "";
  try {
    const q = new URLSearchParams({ student_id: sid });
    const [sum, portrait] = await Promise.all([
      apiGet(`/api/me/summary?${q}`),
      apiGet(`/api/students/${encodeURIComponent(sid)}`).catch(() => null)
    ]);
    summary.value = sum;
    studentInfo.value = portrait?.["学生基本信息"] || {};
    setStudentServerAvatar(studentInfo.value["头像"], sid);
  } catch (e) {
    loadError.value = e.message || "加载失败";
    summary.value = null;
  } finally {
    loading.value = false;
  }
}

function goLogin() {
  close();
  router.push("/login");
}

function goItem(item) {
  close();
  if (item.query) {
    router.push({ path: item.path, query: item.query });
    return;
  }
  router.push(item.path);
}

function onLogout() {
  close();
  logout({ router });
}

async function avatarUploadHandler(file) {
  return uploadStudentAvatar(file, studentId.value);
}

function onBackdropClick() {
  close();
}

function onKeydown(e) {
  if (e.key === "Escape" && props.open) close();
}

watch(
  () => props.open,
  (open) => {
    if (open) loadPanelData();
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("home-user-menu-open", open);
    }
  }
);

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeydown);
  document.documentElement.classList.remove("home-user-menu-open");
});
</script>

<template>
  <Teleport to="body">
    <Transition name="user-menu-fade">
      <button
        v-if="open"
        type="button"
        class="user-menu-backdrop"
        aria-label="关闭我的菜单"
        @click="onBackdropClick"
      />
    </Transition>

    <Transition name="user-menu-slide">
      <aside
        v-if="open"
        class="user-menu-panel"
        role="dialog"
        aria-modal="true"
        aria-label="我的账号"
      >
        <header class="user-menu-head">
          <div class="user-menu-profile">
            <StudentAvatar
              :name="studentName"
              :student-id="studentId"
              :image-url="avatarUrl"
              size="lg"
              editable
              :upload-handler="avatarUploadHandler"
              title="点击修改头像"
            />
            <div class="user-menu-meta">
              <strong>{{ guest ? "未登录" : displayStudentName }}</strong>
              <span v-if="guest">登录后查看收藏、关注与个人数据</span>
              <span v-else>{{ displayStudentId }} · {{ studentMajor }}</span>
            </div>
          </div>
          <button type="button" class="user-menu-close" aria-label="关闭" @click="close">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </button>
        </header>

        <div v-if="guest" class="user-menu-guest">
          <p>请先登录以使用收藏、关注、评价等功能。</p>
          <button type="button" class="user-menu-primary" @click="goLogin">前往登录</button>
        </div>

        <template v-else>
          <p v-if="loadError" class="user-menu-error">{{ loadError }}</p>

          <div v-if="statItems.length" class="user-menu-stats">
            <div v-for="s in statItems" :key="s.label" class="user-menu-stat">
              <strong>{{ s.value }}</strong>
              <span>{{ s.label }}</span>
            </div>
          </div>
          <div v-else-if="loading" class="user-menu-loading">加载中…</div>

          <nav class="user-menu-nav" aria-label="账号快捷入口">
            <button
              v-for="item in menuItems"
              :key="item.key"
              type="button"
              class="user-menu-item"
              @click="goItem(item)"
            >
              <span class="user-menu-item-icon" aria-hidden="true">
                <svg v-if="item.icon === 'profile'" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6" />
                  <path d="M5 20c1.2-3.5 4-5.5 7-5.5s5.8 2 7 5.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </svg>
                <svg v-else-if="item.icon === 'fav'" viewBox="0 0 24 24" fill="none">
                  <path d="M12 20.5 4.5 12.8a5.2 5.2 0 0 1 0-7.4 5.2 5.2 0 0 1 7.4 0L12 7.5l.1-.1a5.2 5.2 0 0 1 7.3 0 5.2 5.2 0 0 1 0 7.4L12 20.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                </svg>
                <svg v-else-if="item.icon === 'fol'" viewBox="0 0 24 24" fill="none">
                  <rect x="4" y="8" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.6" />
                  <path d="M9 8V6.5A1.5 1.5 0 0 1 10.5 5h3A1.5 1.5 0 0 1 15 6.5V8M8 14h3M8 17h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </svg>
                <svg v-else-if="item.icon === 'interview'" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="4" width="18" height="13" rx="2" stroke="currentColor" stroke-width="1.6" />
                  <path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6" />
                  <path d="M6 20v-1.2A4 4 0 0 1 10 4h4a4 4 0 0 1 4 4.8V20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </svg>
              </span>
              <span class="user-menu-item-label">{{ item.label }}</span>
              <svg class="user-menu-item-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m9 6 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </nav>

          <footer v-if="isLoggedIn()" class="user-menu-foot">
            <button type="button" class="user-menu-logout" @click="onLogout">退出登录</button>
          </footer>
        </template>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.user-menu-backdrop {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: var(--home-sidebar-w, 108px);
  z-index: var(--home-user-menu-backdrop-z, 1200);
  border: none;
  padding: 0;
  margin: 0;
  background: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(2px);
  cursor: default;
}
.user-menu-panel {
  position: fixed;
  top: 0;
  bottom: 0;
  left: var(--home-sidebar-w, 108px);
  z-index: var(--home-user-menu-panel-z, 1210);
  width: min(300px, calc(100vw - var(--home-sidebar-w, 108px) - 16px));
  display: flex;
  flex-direction: column;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-left: none;
  border-radius: 0 var(--home-radius-lg, 16px) var(--home-radius-lg, 16px) 0;
  box-shadow: 8px 0 32px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}
.user-menu-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 16px 16px 14px;
  background: linear-gradient(135deg, rgba(91, 106, 223, 0.08), rgba(99, 102, 241, 0.03));
  border-bottom: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
}
.user-menu-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.user-menu-avatar {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(145deg, #c7d2fe, #818cf8);
  color: #312e81;
  font-size: 1rem;
  font-weight: 800;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.25);
}
.user-menu-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.user-menu-meta strong {
  font-size: 0.95rem;
  color: #0f172a;
  line-height: 1.2;
}
.user-menu-meta span {
  font-size: 0.74rem;
  color: #64748b;
  line-height: 1.35;
  word-break: break-all;
}
.user-menu-close {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: #64748b;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background 0.15s, color 0.15s;
}
.user-menu-close:hover {
  background: #fff;
  color: #334155;
}
.user-menu-close svg {
  width: 16px;
  height: 16px;
}
.user-menu-guest {
  padding: 18px 16px 20px;
}
.user-menu-guest p {
  margin: 0 0 14px;
  font-size: 0.84rem;
  color: #64748b;
  line-height: 1.5;
}
.user-menu-primary {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
}
.user-menu-primary:hover {
  filter: brightness(1.03);
}
.user-menu-error {
  margin: 12px 16px 0;
  font-size: 0.8rem;
  color: #b91c1c;
  font-weight: 600;
}
.user-menu-loading {
  padding: 14px 16px;
  font-size: 0.82rem;
  color: #94a3b8;
}
.user-menu-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 12px 16px;
}
.user-menu-stat {
  border: 1px solid #e8ecff;
  border-radius: 12px;
  padding: 10px 12px;
  background: #f8faff;
  text-align: center;
}
.user-menu-stat strong {
  display: block;
  font-size: 1.1rem;
  color: var(--home-primary, #5b6adf);
  line-height: 1.2;
}
.user-menu-stat span {
  display: block;
  margin-top: 2px;
  font-size: 0.68rem;
  color: #64748b;
}
.user-menu-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 10px 10px;
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 10px 12px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}
.user-menu-item:hover {
  background: #eef2ff;
  color: var(--home-primary, #5b6adf);
}
.user-menu-item-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #f1f5ff;
  color: var(--home-primary, #5b6adf);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.user-menu-item-icon svg {
  width: 18px;
  height: 18px;
}
.user-menu-item-label {
  flex: 1;
  font-size: 0.86rem;
  font-weight: 600;
}
.user-menu-item-arrow {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  flex-shrink: 0;
}
.user-menu-foot {
  margin-top: auto;
  flex-shrink: 0;
  padding: 10px 16px 14px;
  border-top: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: var(--home-card-bg, #fff);
}
.user-menu-logout {
  width: 100%;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 9px 12px;
  background: #fff;
  color: #b91c1c;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}
.user-menu-logout:hover {
  background: #fef2f2;
}
.user-menu-fade-enter-active,
.user-menu-fade-leave-active {
  transition: opacity 0.2s ease;
}
.user-menu-fade-enter-from,
.user-menu-fade-leave-to {
  opacity: 0;
}
.user-menu-slide-enter-active,
.user-menu-slide-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.user-menu-slide-enter-from,
.user-menu-slide-leave-to {
  opacity: 0;
  transform: translateX(-100%);
}
@media (max-width: 900px) {
  .user-menu-backdrop,
  .user-menu-panel {
    left: 80px;
  }
  .user-menu-panel {
    width: min(280px, calc(100vw - 88px));
  }
}
</style>
