<template>
  <div class="board" data-testid="pipeline-board">
    <div v-for="col in columns" :key="col" class="col">
      <h3>{{ labels[col] }}</h3>
      <div
        v-for="app in apps.filter(a => a.status === col)"
        :key="app.id"
        class="app-card"
      >
        <strong>{{ app.candidate_name || "Candidate" }}</strong>
        <div class="muted">Score {{ formatScore(app.keyword_score) }}</div>
        <div v-if="app.llm_score != null" class="muted">LLM {{ app.llm_score }}</div>
        <slot name="actions" :app="app" />
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: { apps: { type: Array, default: () => [] } },
  data() {
    return {
      columns: ["applied", "screened", "interview", "offer", "rejected"],
      labels: {
        applied: "Applied",
        screened: "Screened",
        interview: "Interview",
        offer: "Offer",
        rejected: "Rejected",
      },
    };
  },
  methods: {
    formatScore(s) {
      if (s == null) return "—";
      return Math.round(s * 100) + "%";
    },
  },
};
</script>
