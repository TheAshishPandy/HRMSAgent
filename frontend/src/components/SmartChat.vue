<template>
  <div class="sc" v-if="visible">
    <button
      v-if="!open"
      class="sc-fab"
      type="button"
      aria-label="Open Smart Chat"
      @click="openPanel"
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M4 12a8 8 0 1 1 3.2 6.4L4 20l1.1-3.2A7.9 7.9 0 0 1 4 12Z" />
        <path d="M8 12h.01M12 12h.01M16 12h.01" stroke-linecap="round" />
      </svg>
    </button>
    <section v-else class="sc-panel" role="dialog" aria-label="Smart Chat" aria-modal="false">
      <header class="sc-head">
        <div>
          <p class="sc-kicker">Smart Chat</p>
          <p class="sc-who">{{ who }}</p>
        </div>
        <div class="sc-head-actions">
          <button type="button" class="sc-icon" aria-label="New chat" @click="newChat">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M12 5v14M5 12h14" stroke-linecap="round" />
            </svg>
          </button>
          <button type="button" class="sc-icon" aria-label="Close Smart Chat" @click="open = false">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </header>
      <div class="sc-body">
        <aside class="sc-side" v-if="conversations.length">
          <p class="sc-side-label">Recent</p>
          <button
            v-for="c in conversations"
            :key="c.id"
            type="button"
            class="sc-conv"
            :class="{ on: c.id === conversationId }"
            @click="loadConv(c.id)"
          >{{ c.title }}</button>
        </aside>
        <div class="sc-main">
          <div class="sc-log" ref="log">
            <div v-if="!messages.length" class="sc-hello">
              <p>Hello{{ ctx && ctx.name ? ', ' + firstName : '' }}. I already know who you are from this login.</p>
              <p class="muted">Ask about leave, payroll, attendance, policies, or your applications. I will not ask for your employee or candidate ID.</p>
            </div>
            <article v-for="(m, i) in messages" :key="i" class="sc-msg" :data-role="m.role">
              <p class="sc-role">{{ m.role === 'user' ? 'You' : 'Assistant' }}</p>
              <div class="md">{{ m.content }}</div>
              <ul v-if="m.sources && m.sources.length" class="sc-src">
                <li v-for="(s, si) in m.sources" :key="si">{{ s.title }}{{ s.section ? ' · ' + s.section : '' }}</li>
              </ul>
              <div v-if="m.cards && m.cards.length" class="sc-cards">
                <div v-for="(card, ci) in m.cards" :key="ci" class="sc-card">
                  <h3>{{ card.title }}</h3>
                  <p v-for="(it, ii) in card.items" :key="ii"><span>{{ it.label }}</span> {{ it.value }}</p>
                </div>
              </div>
            </article>
            <p v-if="loading" class="sc-wait" aria-live="polite">Looking up your records…</p>
            <p v-if="error" class="error" role="alert">{{ error }}</p>
          </div>
          <form class="sc-form" @submit.prevent="send">
            <label class="sr-only" for="sc-input">Ask anything</label>
            <textarea
              id="sc-input"
              v-model="draft"
              rows="2"
              :disabled="loading"
              placeholder="Ask anything about your work or application…"
              @keydown.enter.exact.prevent="send"
            />
            <button type="submit" :disabled="loading || !draft.trim()">Send</button>
          </form>
        </div>
      </div>
    </section>
  </div>
</template>
<script>
import { api } from "../api";
import { auth } from "../stores/auth";

export default {
  data: () => ({
    open: false,
    draft: "",
    loading: false,
    error: "",
    messages: [],
    conversations: [],
    conversationId: null,
    ctx: null,
  }),
  computed: {
    visible() {
      return !!(auth.user && auth.token);
    },
    who() {
      if (!this.ctx) return "Signed in";
      const kind = this.ctx.user_type === "candidate" ? "Candidate" : "Employee";
      return `${kind} · ${this.ctx.name || "Online"}`;
    },
    firstName() {
      const n = (this.ctx && this.ctx.name) || "";
      return n.split(" ")[0];
    },
  },
  watch: {
    visible(v) {
      if (v) this.boot();
    },
  },
  created() {
    if (this.visible) this.boot();
  },
  methods: {
    async boot() {
      try {
        this.ctx = await api("/api/chat/context");
        this.conversations = await api("/api/chat/conversations");
      } catch {
        this.ctx = null;
      }
    },
    openPanel() {
      this.open = true;
      this.boot();
    },
    newChat() {
      this.conversationId = null;
      this.messages = [];
      this.error = "";
    },
    async loadConv(id) {
      this.conversationId = id;
      const data = await api(`/api/chat/conversations/${id}`);
      this.messages = (data.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        cards: [],
      }));
    },
    async send() {
      const text = this.draft.trim();
      if (!text || this.loading) return;
      this.error = "";
      this.messages.push({ role: "user", content: text, sources: [], cards: [] });
      this.draft = "";
      this.loading = true;
      try {
        const data = await api("/api/chat/messages", {
          method: "POST",
          body: JSON.stringify({ message: text, conversation_id: this.conversationId }),
        });
        this.conversationId = data.conversation_id;
        this.messages.push({
          role: "assistant",
          content: data.reply,
          sources: data.sources || [],
          cards: data.cards || [],
        });
        this.conversations = await api("/api/chat/conversations");
      } catch (e) {
        this.error = e.message || "Could not send message";
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          const el = this.$refs.log;
          if (el) el.scrollTop = el.scrollHeight;
        });
      }
    },
  },
};
</script>
