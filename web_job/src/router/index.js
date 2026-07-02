import { createRouter, createWebHistory } from "vue-router";
import HomeLayout from "../layouts/HomeLayout.vue";
import LoginView from "../views/LoginView.vue";
import StudentView from "../views/StudentView.vue";
import JobsView from "../views/JobsView.vue";
import CompaniesView from "../views/CompaniesView.vue";
import ChatView from "../views/ChatView.vue";
import ResumeCreateView from "../views/ResumeCreateView.vue";
import ToolsView from "../views/ToolsView.vue";
import MeView from "../views/MeView.vue";
import InterviewCenterView from "../views/InterviewCenterView.vue";
import InterviewIndustryManageView from "../views/InterviewIndustryManageView.vue";
import InterviewCategoryManageView from "../views/InterviewCategoryManageView.vue";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    { path: "/", redirect: "/login" },
    { path: "/login", component: LoginView },
    {
      path: "/",
      component: HomeLayout,
      meta: { homeLayout: true },
      children: [
        { path: "student", component: StudentView },
        { path: "resume", redirect: "/resume/create" },
        { path: "resume/create", component: ResumeCreateView },
        { path: "interview", redirect: "/interview/center" },
        { path: "interview/center", component: InterviewCenterView },
        {
          path: "interview/center/room/:recordId",
          component: () => import("../views/InterviewCenterRoomView.vue")
        },
        { path: "interview/industry", component: InterviewIndustryManageView },
        { path: "interview/categories", component: InterviewCategoryManageView },
        { path: "interview/plans", redirect: "/interview/industry" },
        {
          path: "interview/plans/:planId",
          redirect: (to) => ({
            path: "/interview/industry",
            query: { planId: to.params.planId, ...to.query }
          })
        },
        { path: "jobs", component: JobsView },
        { path: "me", component: MeView },
        {
          path: "me/interviews/:recordId",
          component: () => import("../views/InterviewRecordDetailView.vue")
        },
        { path: "student-chat", component: ChatView }
      ]
    },
    { path: "/jobs/:job_id", component: () => import("../views/JobDetailView.vue") },
    { path: "/companies", component: CompaniesView },
    { path: "/companies/:credit_code", component: () => import("../views/CompanyDetailView.vue") },
    { path: "/tools", component: ToolsView },
    {
      path: "/data-search",
      redirect: (to) => ({ path: "/tools", query: { ...to.query, tab: "search" } })
    },
    {
      path: "/ai-search",
      redirect: (to) => ({ path: "/tools", query: { ...to.query, tab: "ai-search" } })
    },
    {
      path: "/ocr",
      redirect: (to) => ({ path: "/tools", query: { ...to.query, tab: "ocr" } })
    }
  ]
});

export default router;
