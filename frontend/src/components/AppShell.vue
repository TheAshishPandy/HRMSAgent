<template>
  <div class="shell">
    <aside class="nav">
      <router-link class="brand" :to="home">Northstar ATS</router-link>
      <template v-if="isHr">
        <router-link to="/hr">Dashboard</router-link>
        <router-link to="/hr/jobs">Jobs</router-link>
        <router-link to="/hr/calendar">Calendar</router-link>
        <router-link to="/hr/inbox">Inbox</router-link>
        <router-link to="/hr/settings">Settings</router-link>
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
    home() { return this.isHr ? "/hr" : "/me"; },
  },
  methods: {
    out() {
      logout();
      this.$router.push("/login");
    },
  },
};
</script>
