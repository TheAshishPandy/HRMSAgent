<template>
  <div>
    <h1>Settings</h1>
    <div class="card">
      <p>SMTP: {{ on(i.smtp_configured) }}</p>
      <p>Google Calendar: {{ on(i.google_configured) }} {{ i.google_connected ? "(connected)" : "" }}</p>
      <p>LLM ranking: {{ on(i.llm_configured) }}</p>
      <p class="muted">Secrets are never displayed. Configure them in the server environment.</p>
    </div>
  </div>
</template>
<script>
import { auth } from "../stores/auth";
export default {
  computed: {
    i() { return (auth.user && auth.user.integrations) || {}; },
  },
  methods: {
    on(v) { return v ? "configured" : "missing"; },
  },
};
</script>
