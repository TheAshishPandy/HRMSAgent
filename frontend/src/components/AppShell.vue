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
        <router-link v-if="mod('attendance')" to="/hr/attendance">Attendance</router-link>
        <router-link v-if="mod('leave')" to="/hr/leave">Leave</router-link>
        <router-link v-if="mod('payroll')" to="/hr/payroll">Payroll</router-link>
        <router-link v-if="mod('recruitment')" to="/hr/jobs">Jobs</router-link>
        <router-link v-if="mod('recruitment')" to="/hr/calendar">Calendar</router-link>
        <router-link to="/hr/inbox">Inbox</router-link>
        <router-link to="/hr/settings">Settings</router-link>
      </template>
      <template v-else-if="isEmployee">
        <router-link to="/work">My work</router-link>
        <router-link v-if="mod('leave')" to="/work/leave">Leave</router-link>
        <router-link v-if="mod('payroll')" to="/work/payslips">Payslips</router-link>
      </template>
      <template v-else>
        <router-link to="/me">My applications</router-link>
        <router-link to="/me/inbox">Inbox</router-link>
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
import { auth, logout } from "../stores/auth";
export default {
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
  methods: {
    mod(name) {
      if (!this.modules.length) return true;
      return this.modules.includes(name);
    },
    out() {
      logout();
      this.$router.push("/login");
    },
  },
};
</script>
