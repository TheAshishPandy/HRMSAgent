<template>
  <div>
    <h1>{{ id ? "Edit job" : "New job" }}</h1>
    <form class="card" @submit.prevent="save">
      <div class="grid cols-2">
        <div class="field"><label>Title</label><input v-model="form.title" required /></div>
        <div class="field"><label>Team</label><input v-model="form.team" required /></div>
        <div class="field"><label>Location</label><input v-model="form.location" required /></div>
        <div class="field"><label>Seniority</label><input v-model="form.seniority" required /></div>
        <div class="field"><label>Required skills (comma)</label><input v-model="skills" /></div>
        <div class="field"><label>Nice to have (comma)</label><input v-model="nice" /></div>
        <div class="field"><label>Min years</label><input v-model.number="form.min_years" type="number" min="0" /></div>
        <div class="field">
          <label>Education</label>
          <select v-model="form.education">
            <option value="none">None</option>
            <option value="bachelor">Bachelor</option>
            <option value="master">Master</option>
            <option value="phd">PhD</option>
          </select>
        </div>
      </div>
      <div class="field"><label>Narrative</label><textarea v-model="form.narrative" rows="4"></textarea></div>
      <div v-if="form.jd_markdown" class="field"><label>Job description</label><textarea v-model="form.jd_markdown" rows="10"></textarea></div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="row">
        <button type="submit">Save</button>
        <button v-if="id" type="button" class="secondary" @click="publish">Publish</button>
        <button v-if="id" type="button" class="ghost" @click="closeJob">Close</button>
        <a v-if="id" :href="'/api/jobs/' + id + '/export.md'">Export Markdown</a>
      </div>
    </form>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({
    form: { title: "", team: "", location: "", seniority: "", min_years: 0, education: "none", narrative: "", jd_markdown: "" },
    skills: "",
    nice: "",
    error: "",
  }),
  computed: { id() { return this.$route.params.id; } },
  async created() {
    if (!this.id) return;
    const j = await api("/api/jobs/" + this.id);
    this.form = { ...this.form, ...j };
    this.skills = (j.required_skills || []).join(", ");
    this.nice = (j.nice_to_have || []).join(", ");
  },
  methods: {
    payload() {
      return {
        ...this.form,
        required_skills: this.skills.split(",").map((s) => s.trim()).filter(Boolean),
        nice_to_have: this.nice.split(",").map((s) => s.trim()).filter(Boolean),
      };
    },
    async save() {
      this.error = "";
      try {
        const body = this.payload();
        let j;
        if (this.id) j = await api("/api/jobs/" + this.id, { method: "PATCH", body: JSON.stringify(body) });
        else j = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
        this.$router.push("/hr/jobs/" + j.id + "/edit");
        this.form.jd_markdown = j.jd_markdown;
      } catch (e) {
        this.error = e.message || "Save failed";
      }
    },
    async publish() {
      await api("/api/jobs/" + this.id + "/publish", { method: "POST" });
    },
    async closeJob() {
      await api("/api/jobs/" + this.id + "/close", { method: "POST" });
    },
  },
};
</script>
