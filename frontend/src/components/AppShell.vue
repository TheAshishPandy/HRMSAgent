<template>
  <div class="shell">
    <aside class="nav">
      <router-link class="brand" :to="home">{{ brand }}</router-link>
      <template v-if="isAdmin">
        <router-link to="/admin">Organizations</router-link>
      </template>
      <template v-else-if="isHr">
        <router-link to="/hr">Dashboard</router-link>
        <router-link to="/hr/employees">Employees</router-link>
        <router-link to="/hr/attendance">Attendance</router-link>
        <router-link to="/hr/leave">Leave</router-link>
        <router-link to="/hr/jobs">Jobs</router-link>
        <router-link to="/hr/calendar">Calendar</router-link>
        <router-link to="/hr/inbox">Inbox</router-link>
        <router-link to="/hr/settings">Settings</router-link>
      </template>
      <template v-else-if="isEmployee">
        <router-link to="/work">My work</router-link>
        <router-link to="/work/leave">Leave</router-link>
      </template>
      <template v-else>
        <router-link to="/me">My applications</router-link>
        <router-link to="/me/inbox">Inbox</router-link>
        <router-link to="/">Open roles</router-link>
      </template>
      <button class="ghost" style="margin-top:24px;width:100%;color:#e7dfd3;border-color:#57534e" @click="out">Sign out</button>
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
    brand() { return (auth.user && auth.user.organization && auth.user.organization.name) || "Northstar HRMS"; },
  },
  methods: {
    out() {
      logout();
      this.$router.push("/login");
    },
  },
};
</script>
