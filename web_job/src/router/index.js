import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import StudentView from "../views/StudentView.vue";
import JobsView from "../views/JobsView.vue";
import CompaniesView from "../views/CompaniesView.vue";
import ChatView from "../views/ChatView.vue";
import JobDetailView from "../views/JobDetailView.vue";
import CompanyDetailView from "../views/CompanyDetailView.vue";
import ResumeCreateView from "../views/ResumeCreateView.vue";
import ToolsView from "../views/ToolsView.vue";
import MeView from "../views/MeView.vue";
import InterviewPlanListView from "../views/InterviewPlanListView.vue";
import InterviewPlanDetailView from "../views/InterviewPlanDetailView.vue";
import InterviewIndustryManageView from "../views/InterviewIndustryManageView.vue";
import InterviewRecordDetailView from "../views/InterviewRecordDetailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/login" },
    { path: "/login", component: LoginView },
    { path: "/student", component: StudentView },
    { path: "/resume", redirect: "/resume/create" },
    { path: "/resume/create", component: ResumeCreateView },
    { path: "/jobs", component: JobsView },
    { path: "/jobs/:job_id", component: JobDetailView },
    { path: "/companies", component: CompaniesView },
    { path: "/companies/:credit_code", component: CompanyDetailView },
    { path: "/me", component: MeView },
    { path: "/me/interviews/:recordId", component: InterviewRecordDetailView },
    { path: "/interview/plans", component: InterviewPlanListView },
    { path: "/interview/plans/:planId", component: InterviewPlanDetailView },
    { path: "/interview/industry", component: InterviewIndustryManageView },
    { path: "/student-chat", component: ChatView },
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
