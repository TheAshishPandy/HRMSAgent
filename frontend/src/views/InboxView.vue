<template>
  <div>
    <h1>Inbox</h1>
    <div v-for="m in messages" :key="m.id" class="card" style="margin-bottom:12px">
      <strong>{{ m.subject }}</strong>
      <p class="muted">{{ m.created_at }} {{ m.smtp_sent_at ? "SMTP sent" : "in-app only" }}</p>
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
  async created() {
    this.messages = await api("/api/messages");
  },
  methods: {
    async read(m) {
      await api("/api/messages/" + m.id + "/read", { method: "POST" });
      m.read_at = new Date().toISOString();
    },
  },
};
</script>
