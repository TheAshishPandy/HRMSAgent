<template>
  <div class="shell" :data-layout="layoutKey">
    <aside class="nav">
      <router-link class="brand" :to="home">
        <img v-if="logo" :src="logo" alt="" class="brand-logo" />
        {{ brand }}
      </router-link>
      <template v-if="isAdmin">
        <router-link to="/admin">Organizations</router-link>
        <router-link to="/admin/studio">Design studio</router-link>
      </template>
      <template v-else-if="isHr">
        <router-link v-if="mod('dashboard')" to="/hr">Dashboard</router-link>
        <router-link v-if="mod('employees')" to="/hr/employees">Employees</router-link>
        <router-link v-if="mod('employees')" to="/hr/onboarding">Onboarding</router-link>
        <router-link v-if="mod('attendance')" to="/hr/attendance">Attendance</router-link>
        <router-link v-if="mod('leave')" to="/hr/leave">Leave</router-link>
        <router-link v-if="mod('payroll')" to="/hr/payroll">Payroll</router-link>
        <router-link v-if="mod('recruitment')" to="/hr/jobs">Jobs</router-link>
        <router-link v-if="mod('recruitment')" to="/hr/calendar">Calendar</router-link>
        <router-link to="/hr/inbox">
          Inbox
          <span v-if="unread" class="badge">{{ unread }}</span>
        </router-link>
        <router-link to="/hr/settings">Settings</router-link>
      </template>
      <template v-else-if="isEmployee">
        <router-link to="/work">My work</router-link>
        <router-link v-if="mod('leave')" to="/work/leave">Leave</router-link>
        <router-link v-if="mod('payroll')" to="/work/payslips">Payslips</router-link>
        <router-link to="/work/onboarding">Onboarding</router-link>
        <router-link to="/work/inbox">
          Inbox
          <span v-if="unread" class="badge">{{ unread }}</span>
        </router-link>
      </template>
      <template v-else>
        <router-link to="/me">My applications</router-link>
        <router-link to="/me/inbox">
          Inbox
          <span v-if="unread" class="badge">{{ unread }}</span>
        </router-link>
        <router-link to="/">Open roles</router-link>
      </template>
      <button class="ghost signout" @click="out">Sign out</button>
    </aside>
    <main class="main">
      <slot />
    </main>
  </div>
</template>
<script>
import { api } from "../api";
import { auth, logout } from "../stores/auth";
export default {
  data: () => ({ unread: 0, timer: null }),
  computed: {
    isHr() { return auth.user && auth.user.role === "hr"; },
    isAdmin() { return auth.user && auth.user.role === "super_admin"; },
    isEmployee() { return auth.user && auth.user.role === "employee"; },
    home() { return this.isAdmin ? "/admin" : this.isHr ? "/hr" : this.isEmployee ? "/work" : "/me"; },
    org() { return (auth.user && auth.user.organization) || null; },
    brand() { return (this.org && this.org.name) || "Northstar HRMS"; },
    logo() { return this.org && this.org.logo_url; },
    layoutKey() { return (this.org && this.org.layout_key) || "classic_sidebar"; },
    modules() { return (this.org && this.org.modules) || []; },
  },
  async created() {
    this.loadUnread();
    this.timer = setInterval(this.loadUnread, 15000);
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer);
  },
  methods: {
    mod(name) {
      if (!this.modules.length) return true;
      return this.modules.includes(name);
    },
    async loadUnread() {
      try {
        const data = await api("/api/messages/unread-count");
        this.unread = data.unread || 0;
      } catch (e) {
        /* auth nav only */
      }
    },
    out() {
      logout();
      this.$router.push("/login");
    },
  },
};
</script>
<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #dc2626;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  margin-left: 6px;
}
</style>
