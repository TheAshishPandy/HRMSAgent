import { createRouter, createWebHistory } from "vue-router";
import { auth, loadMe } from "./stores/auth";

const routes = [
  { path: "/", name: "public-jobs", component: () => import("./views/PublicJobsView.vue") },
  { path: "/jobs/:id", name: "public-job", component: () => import("./views/PublicJobDetailView.vue") },
  { path: "/login", name: "login", component: () => import("./views/LoginView.vue") },
  { path: "/register", name: "register", component: () => import("./views/RegisterView.vue") },
  { path: "/hr", name: "hr-dash", component: () => import("./views/HrDashboard.vue"), meta: { role: "hr" } },
  { path: "/hr/jobs", name: "hr-jobs", component: () => import("./views/JobsListView.vue"), meta: { role: "hr" } },
  { path: "/hr/jobs/new", name: "hr-job-new", component: () => import("./views/JobEditView.vue"), meta: { role: "hr" } },
  { path: "/hr/jobs/:id/edit", name: "hr-job-edit", component: () => import("./views/JobEditView.vue"), meta: { role: "hr" } },
  { path: "/hr/jobs/:id/pipeline", name: "pipeline", component: () => import("./views/PipelineView.vue"), meta: { role: "hr" } },
  { path: "/hr/applications/:id", name: "app-detail", component: () => import("./views/ApplicationDetailView.vue"), meta: { role: "hr" } },
  { path: "/hr/calendar", name: "calendar", component: () => import("./views/CalendarView.vue"), meta: { role: "hr" } },
  { path: "/hr/inbox", name: "hr-inbox", component: () => import("./views/InboxView.vue"), meta: { role: "hr" } },
  { path: "/hr/settings", name: "settings", component: () => import("./views/SettingsView.vue"), meta: { role: "hr" } },
  { path: "/me", name: "cand-dash", component: () => import("./views/CandidateDashboard.vue"), meta: { role: "candidate" } },
  { path: "/me/applications/:id", name: "cand-app", component: () => import("./views/CandidateApplicationView.vue"), meta: { role: "candidate" } },
  { path: "/me/inbox", name: "cand-inbox", component: () => import("./views/InboxView.vue"), meta: { role: "candidate" } },
];

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  if (!auth.user && auth.token) await loadMe();
  if (to.meta.role && !auth.user) return { path: "/login", query: { next: to.fullPath } };
  if (to.meta.role && auth.user && auth.user.role !== to.meta.role) {
    return auth.user.role === "hr" ? "/hr" : "/me";
  }
  return true;
});

export default router;
