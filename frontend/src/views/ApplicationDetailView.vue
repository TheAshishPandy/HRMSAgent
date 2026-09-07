<template>
  <div v-if="app">
    <h1>{{ app.candidate_name }}</h1>
    <p class="muted">{{ app.job_title }} · {{ app.candidate_email }} · <span class="pill">{{ app.status }}</span></p>
    <div class="grid cols-2" style="margin-top:16px">
      <div class="card">
        <h2>Screening</h2>
        <p>Keyword {{ pct(app.keyword_score) }}</p>
        <pre class="muted">{{ JSON.stringify(app.score_breakdown, null, 2) }}</pre>
        <p v-if="app.llm_score != null">LLM {{ app.llm_score }} — {{ app.llm_rationale }}</p>
        <p v-if="app.parse_error" class="error">Parse error: {{ app.parse_error }}</p>
        <div class="field">
          <label>Paste resume text to retry</label>
          <textarea v-model="paste" rows="4"></textarea>
        </div>
        <div class="row">
          <button class="secondary" type="button" @click="retry">Rescore</button>
          <button type="button" @click="override('pass')">Pass</button>
          <button class="danger" type="button" @click="override('fail')">Fail</button>
          <a v-if="app.has_resume" :href="'/api/applications/' + app.id + '/resume'" target="_blank">Resume</a>
        </div>
        <div class="md" style="margin-top:12px">{{ app.parsed_text }}</div>
      </div>
      <div class="card">
        <h2>Interview and decision</h2>
        <StatusBanner :text="banner" />
        <div class="field">
          <label>Start (UTC ISO)</label>
          <input v-model="startAt" placeholder="2026-09-07T14:00:00Z" />
        </div>
        <button type="button" @click="schedule">Propose interview</button>
        <div v-for="iv in app.interviews" :key="iv.id" class="app-card" style="margin-top:12px">
          <div>{{ iv.start_at }} · {{ iv.status }}</div>
          <div class="row">
            <button class="ghost" type="button" @click="ivAction(iv.id, 'complete')">Complete</button>
          </div>
          <div class="field">
            <label>Feedback rating 1-5</label>
            <input v-model.number="rating" type="number" min="1" max="5" />
          </div>
          <textarea v-model="notes" rows="3" placeholder="Notes"></textarea>
          <button class="secondary" type="button" @click="sendFeedback(iv.id)">Save feedback</button>
        </div>
        <div class="row" style="margin-top:16px">
          <button class="secondary" type="button" @click="advance('shortlist')">Shortlist</button>
          <button class="secondary" type="button" @click="advance('technical')">Technical</button>
          <button class="secondary" type="button" @click="advance('hr_round')">HR round</button>
          <button type="button" @click="decide('offer')">Send offer</button>
          <button class="danger" type="button" @click="decide('reject')">Reject</button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>
<script>
import { api } from "../api";
import { auth } from "../stores/auth";
import StatusBanner from "../components/StatusBanner.vue";
export default {
  components: { StatusBanner },
  data: () => ({ app: null, paste: "", startAt: "", rating: 4, notes: "", error: "" }),
  computed: {
    banner() {
      const i = auth.user && auth.user.integrations;
      if (i && !i.smtp_configured) return "SMTP is not configured. Messages stay in the in-app inbox.";
      return "";
    },
  },
  async created() { await this.reload(); },
  methods: {
    pct(s) { return s == null ? "—" : Math.round(s * 100) + "%"; },
    async reload() {
      this.app = await api("/api/applications/" + this.$route.params.id);
    },
    async override(decision) {
      await api("/api/applications/" + this.app.id + "/override", { method: "POST", body: JSON.stringify({ decision }) });
      await this.reload();
    },
    async retry() {
      await api("/api/applications/" + this.app.id + "/parsed-text", { method: "POST", body: JSON.stringify({ text: this.paste }) });
      await this.reload();
    },
    async schedule() {
      this.error = "";
      try {
        await api("/api/interviews", {
          method: "POST",
          body: JSON.stringify({ application_id: this.app.id, start_at: this.startAt }),
        });
        await this.reload();
      } catch (e) {
        this.error = (e.payload && e.payload.detail && e.payload.detail.message) || e.message;
      }
    },
    async ivAction(id, action) {
      await api("/api/interviews/" + id + "/" + action, { method: "POST" });
      await this.reload();
    },
    async sendFeedback(id) {
      await api("/api/feedback", { method: "POST", body: JSON.stringify({ interview_id: id, rating: this.rating, notes: this.notes }) });
    },
    async decide(kind) {
      this.error = "";
      try {
        await api("/api/applications/" + this.app.id + "/" + kind, { method: "POST" });
        await this.reload();
      } catch (e) {
        this.error = (e.payload && e.payload.detail && e.payload.detail.message) || e.message;
      }
    },
    async advance(status) {
      this.error = "";
      try {
        await api("/api/applications/" + this.app.id + "/advance", {
          method: "POST",
          body: JSON.stringify({ status }),
        });
        await this.reload();
      } catch (e) {
        this.error = (e.payload && e.payload.detail && e.payload.detail.message) || e.message;
      }
    },
  },
};
</script>
