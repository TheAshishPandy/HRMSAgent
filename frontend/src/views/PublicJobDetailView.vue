<template>
  <div class="main">
    <router-link to="/">All roles</router-link>
    <div v-if="job" class="grid cols-2" style="margin-top:16px">
      <div class="card">
        <h1>{{ job.title }}</h1>
        <div class="md">{{ job.jd_markdown }}</div>
      </div>
      <form class="card" data-testid="apply-form" @submit.prevent="apply">
        <h2>Apply</h2>
        <div class="field">
          <label for="name">Name</label>
          <input id="name" v-model="name" required />
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required />
        </div>
        <div class="field">
          <label for="password">Password (new or existing account)</label>
          <input id="password" v-model="password" type="password" required />
        </div>
        <div class="field">
          <label for="resume">Resume (PDF, DOCX, TXT)</label>
          <input id="resume" type="file" accept=".pdf,.docx,.txt" @change="onFile" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="ok" class="muted">Application submitted. You can sign in to track status.</p>
        <button type="submit">Submit application</button>
      </form>
    </div>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ job: null, name: "", email: "", password: "", file: null, error: "", ok: false }),
  async created() {
    this.job = await api("/api/jobs/" + this.$route.params.id);
  },
  methods: {
    onFile(e) {
      this.file = e.target.files[0];
    },
    async apply() {
      this.error = "";
      if (!this.file) {
        this.error = "Please attach a resume file";
        return;
      }
      const fd = new FormData();
      fd.append("name", this.name);
      fd.append("email", this.email);
      fd.append("password", this.password);
      fd.append("resume", this.file);
      try {
        await api("/api/jobs/" + this.$route.params.id + "/apply", { method: "POST", body: fd });
        this.ok = true;
      } catch (e) {
        this.error = e.message || "Could not apply";
      }
    },
  },
};
</script>
