<script setup>
/**
 * 登录后全局侧栏导航，对齐设计稿：顶部品牌 + 图标菜单 + 底部头像。
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, getStudentId } from "../../api/client";
import { setStudentServerAvatar } from "../../composables/useStudentAvatar";
import { useIsMobile } from "../../composables/useIsMobile";
import HomeUserMenuPanel from "./HomeUserMenuPanel.vue";
import StudentAvatar from "./StudentAvatar.vue";

defineProps({
  /** 简历等全屏页：取消 sticky，与主区顶对齐 */
  flush: { type: Boolean, default: false }
});

const route = useRoute();
const router = useRouter();
const userMenuOpen = ref(false);
const sidebarOpen = ref(false);
const { isMobile } = useIsMobile();

const navItems = [
  { path: "/student", label: "首页", icon: "home" },
  { path: "/student", query: { tab: "profile" }, label: "学生画像", icon: "profile" },
  { path: "/jobs", label: "岗位中心", icon: "jobs" },
  { path: "/resume/create", label: "我的简历", icon: "resume" },
  { path: "/interview/center", label: "面试中心", icon: "center" },
  { path: "/interview/industry", label: "面试分类", icon: "interview" },
  { path: "/interview/categories", label: "行业字典", icon: "dict" },
  { path: "/student-chat", label: "AI助手", icon: "ai" }
];

const studentId = computed(() => getStudentId());
const studentName = ref("");
const isMeActive = computed(() => route.path === "/me" || route.path.startsWith("/me/"));

async function loadStudentName() {
  const sid = studentId.value;
  if (!sid) {
    studentName.value = "";
    return;
  }
  try {
    const data = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
    studentName.value = data?.["学生基本信息"]?.["姓名"] || "";
    setStudentServerAvatar(data?.["学生基本信息"]?.["头像"], sid);
  } catch {
    studentName.value = "";
  }
}

onMounted(loadStudentName);
watch(studentId, loadStudentName);

function isActive(item) {
  const p = route.path;
  const tab = route.query.tab;
  if (item.icon === "profile") return p === "/student" && tab === "profile";
  if (item.icon === "home") return p === "/student" && tab !== "profile";
  if (item.path === "/jobs") return p.startsWith("/jobs");
  if (item.path === "/resume/create") return p.startsWith("/resume");
  if (item.path === "/interview/center") {
    return p.startsWith("/interview/center") || p.startsWith("/me/interviews/");
  }
  if (item.path === "/interview/industry") {
    return p.startsWith("/interview/industry") || p.startsWith("/interview/plans");
  }
  if (item.path === "/interview/categories") return p.startsWith("/interview/categories");
  if (item.path === "/student-chat") return p.startsWith("/student-chat");
  return false;
}

function go(item) {
  userMenuOpen.value = false;
  sidebarOpen.value = false;
  if (item.query) {
    router.push({ path: item.path, query: item.query });
    return;
  }
  router.push(item.path);
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
}

watch(() => route.fullPath, () => {
  userMenuOpen.value = false;
});
</script>

<template>
  <button
    v-if="isMobile"
    type="button"
    class="sidebar-hamburger"
    aria-label="打开菜单"
    @click="sidebarOpen = !sidebarOpen"
  >
    <span class="hamburger-line" />
    <span class="hamburger-line" />
    <span class="hamburger-line" />
  </button>
  <Transition name="sidebar-overlay-fade">
    <div v-if="isMobile && sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false" />
  </Transition>
  <aside
    class="home-sidebar"
    :class="{
      'home-sidebar--flush': flush,
      'home-sidebar--menu-open': userMenuOpen,
      'home-sidebar--mobile': isMobile,
      'home-sidebar--open': sidebarOpen
    }"
    aria-label="主导航"
  >
    <div class="sidebar-brand">智慧就业</div>

    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.label"
        type="button"
        class="sidebar-link"
        :class="{ active: isActive(item) }"
        @click="go(item)"
      >
        <span class="sidebar-icon" aria-hidden="true">
          <svg v-if="item.icon === 'home'" viewBox="0 0 24 24" fill="none">
            <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
          </svg>
          <svg v-else-if="item.icon === 'profile'" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6" />
            <path d="M5 20c1.2-3.5 4-5.5 7-5.5s5.8 2 7 5.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else-if="item.icon === 'jobs'" viewBox="0 0 24 24" fill="none">
            <rect x="4" y="7" width="16" height="13" rx="2" stroke="currentColor" stroke-width="1.6" />
            <path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7" stroke="currentColor" stroke-width="1.6" />
          </svg>
          <svg v-else-if="item.icon === 'resume'" viewBox="0 0 24 24" fill="none">
            <path d="M8 4h8l4 4v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3Z" stroke="currentColor" stroke-width="1.6" />
            <path d="M16 4v4h4M8 12h8M8 16h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else-if="item.icon === 'interview'" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="1.6" />
            <path d="M8 10h8M8 14h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else-if="item.icon === 'center'" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="13" rx="2" stroke="currentColor" stroke-width="1.6" />
            <path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            <circle cx="12" cy="10.5" r="2.5" stroke="currentColor" stroke-width="1.6" />
          </svg>
          <svg v-else-if="item.icon === 'dict'" viewBox="0 0 24 24" fill="none">
            <path d="M6 5.5A2.5 2.5 0 0 1 8.5 3H19v18H8.5A2.5 2.5 0 0 0 6 23V5.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M6 6h10M9 10h7M9 14h7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else-if="item.icon === 'ai'" viewBox="0 0 24 24" fill="none">
            <rect x="5" y="8" width="14" height="10" rx="3" stroke="currentColor" stroke-width="1.6" />
            <circle cx="9.5" cy="13" r="1.2" fill="currentColor" />
            <circle cx="14.5" cy="13" r="1.2" fill="currentColor" />
            <path d="M12 5v2M8 6l1.5 2M16 6l-1.5 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none">
            <path d="M4 6.5h16M4 12h10M4 17.5h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <span class="sidebar-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <button
        type="button"
        class="sidebar-avatar"
        :class="{ 'sidebar-avatar--open': userMenuOpen, 'sidebar-avatar--active': isMeActive && !userMenuOpen }"
        title="我的"
        aria-label="我的"
        aria-haspopup="dialog"
        :aria-expanded="userMenuOpen"
        @click="toggleUserMenu"
      >
        <StudentAvatar
          :name="studentName"
          :student-id="studentId"
          size="fill"
          tone="sidebar"
        />
      </button>
      <span class="sidebar-avatar-label">我的</span>
    </div>

    <HomeUserMenuPanel v-model:open="userMenuOpen" />
  </aside>
</template>

<style scoped>
.home-sidebar {
  width: var(--home-sidebar-w, 108px);
  min-height: 100vh;
  background: var(--home-sidebar-bg);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 18px 10px 16px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  align-self: flex-start;
  z-index: 100;
}
.home-sidebar--flush {
  min-height: 0;
  height: 100%;
  position: relative;
  top: auto;
  align-self: stretch;
  padding-top: 8px;
  z-index: auto;
}
.home-sidebar--menu-open {
  z-index: var(--home-sidebar-raised-z, 1220);
}
.sidebar-brand {
  text-align: center;
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.88rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  margin-bottom: 22px;
  padding: 0 4px;
  line-height: 1.3;
}
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.sidebar-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 100%;
  padding: 10px 6px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  transition: background 0.18s, color 0.18s, box-shadow 0.18s;
}
.sidebar-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}
.sidebar-link.active {
  background: #fff;
  color: var(--home-primary, #5b6adf);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
}
.sidebar-icon {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
}
.sidebar-icon svg {
  width: 20px;
  height: 20px;
}
.sidebar-label {
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1.15;
  text-align: center;
}
.sidebar-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}
.sidebar-avatar {
  border: none;
  cursor: pointer;
  display: block;
  width: 42px;
  height: 42px;
  padding: 0;
  border-radius: 50%;
  overflow: hidden;
  background: transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.18s, transform 0.18s;
}
.sidebar-avatar :deep(.student-avatar) {
  display: block;
  width: 100%;
  height: 100%;
}
.sidebar-avatar :deep(.student-avatar-img) {
  object-fit: cover;
  object-position: center;
}
.sidebar-avatar:hover {
  transform: translateY(-1px);
}
.sidebar-avatar--open {
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.95), 0 4px 14px rgba(15, 23, 42, 0.18);
}
.sidebar-avatar--active {
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.88), 0 4px 14px rgba(15, 23, 42, 0.12);
}
.sidebar-avatar-label {
  font-size: 0.62rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1;
}
@media (max-width: 900px) {
  .home-sidebar {
    width: 80px;
    padding: 14px 6px;
  }
  .sidebar-brand {
    font-size: 0.72rem;
    margin-bottom: 14px;
  }
  .sidebar-label {
    font-size: 0.6rem;
  }
}
.sidebar-hamburger {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 1100;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 8px;
  border: none;
  border-radius: 8px;
  background: var(--home-primary, #5b6adf);
  cursor: pointer;
}
.hamburger-line {
  display: block;
  width: 20px;
  height: 2px;
  background: #fff;
  border-radius: 2px;
}
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1090;
  background: rgba(15, 23, 42, 0.4);
}
.home-sidebar--mobile {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 1095;
  width: 260px;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.15);
}
.home-sidebar--mobile.home-sidebar--open {
  transform: translateX(0);
}
.sidebar-overlay-fade-enter-active,
.sidebar-overlay-fade-leave-active {
  transition: opacity 0.25s ease;
}
.sidebar-overlay-fade-enter-from,
.sidebar-overlay-fade-leave-to {
  opacity: 0;
}
</style>
