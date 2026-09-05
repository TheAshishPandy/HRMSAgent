<template>
  <div class="main">
    <div class="row" style="justify-content:space-between">
      <h1>Open roles</h1>
      <router-link to="/login">Sign in</router-link>
    </div>
    <p class="muted">Internal careers board. Apply with a PDF, DOCX, or TXT resume.</p>
    <div class="grid" style="margin-top:24px">
      <div v-for="j in jobs" :key="j.id" class="card">
        <h2>{{ j.title }}</h2>
        <p class="muted">{{ j.team }} · {{ j.location }} · {{ j.seniority }}</p>
        <router-link :to="'/jobs/' + j.id">View and apply</router-link>
      </div>
      <p v-if="!jobs.length" class="muted">No open jobs yet.</p>
    </div>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ jobs: [] }),
  async created() {
    this.jobs = await api("/api/jobs");
  },
};
</script>
