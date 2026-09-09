<template>
  <div>
    <h1>Inbox</h1>
    <p class="muted">{{ unread }} unread</p>
    <div v-for="m in messages" :key="m.id" class="card" :class="{ unread: !m.read_at }" style="margin-bottom:12px">
      <div class="row" style="justify-content:space-between">
        <strong>{{ m.subject }}</strong>
        <span v-if="!m.read_at" class="pill">Unread</span>
      </div>
      <p class="muted">{{ fmt(m.created_at) }} · {{ m.smtp_sent_at ? "SMTP sent" : "in-app" }}</p>
      <pre class="md">{{ m.body }}</pre>
      <button v-if="!m.read_at" class="ghost" type="button" @click="read(m)">Mark read</button>
    </div>
    <p v-if="!messages.length" class="muted">No messages.</p>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ messages: [] }),
  computed: {
    unread() { return this.messages.filter((m) => !m.read_at).length; },
  },
  async created() {
    this.messages = await api("/api/messages");
  },
  methods: {
    fmt(v) { return v ? new Date(v).toLocaleString() : ""; },
    async read(m) {
      await api("/api/messages/" + m.id + "/read", { method: "POST" });
      m.read_at = new Date().toISOString();
    },
  },
};
</script>
<style scoped>
.unread { border-left: 3px solid var(--primary, #2563eb); }
</style>
