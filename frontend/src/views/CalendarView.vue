<template>
  <div>
    <h1>Calendar</h1>
    <StatusBanner :text="googleMsg" />
    <div class="card">
      <h2>Working hours (Mon-Fri)</h2>
      <div v-for="h in hours" :key="h.weekday" class="row" style="margin-bottom:8px">
        <span style="width:80px">{{ days[h.weekday] }}</span>
        <input v-model="h.start_local" style="max-width:120px" />
        <input v-model="h.end_local" style="max-width:120px" />
      </div>
      <button type="button" @click="saveHours">Save hours</button>
    </div>
    <div class="card" style="margin-top:16px">
      <h2>Busy blocks</h2>
      <div class="row">
        <input v-model="blockStart" placeholder="Start ISO" />
        <input v-model="blockEnd" placeholder="End ISO" />
        <button class="secondary" type="button" @click="addBlock">Add</button>
      </div>
      <ul>
        <li v-for="b in blocks" :key="b.id">{{ b.start_at }} – {{ b.end_at }} <button class="ghost" type="button" @click="delBlock(b.id)">Remove</button></li>
      </ul>
    </div>
  </div>
</template>
<script>
import { api } from "../api";
import { auth } from "../stores/auth";
import StatusBanner from "../components/StatusBanner.vue";
export default {
  components: { StatusBanner },
  data: () => ({
    hours: [],
    blocks: [],
    blockStart: "",
    blockEnd: "",
    days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
  }),
  computed: {
    googleMsg() {
      const i = auth.user && auth.user.integrations;
      if (i && !i.google_configured) return "Google Calendar is not configured. Local weekday hours are used.";
      return "";
    },
  },
  async created() {
    this.hours = await api("/api/calendar/hours");
    this.blocks = await api("/api/calendar/blocks");
  },
  methods: {
    async saveHours() {
      this.hours = await api("/api/calendar/hours", { method: "PUT", body: JSON.stringify({ hours: this.hours }) });
    },
    async addBlock() {
      await api("/api/calendar/blocks", { method: "POST", body: JSON.stringify({ start_at: this.blockStart, end_at: this.blockEnd }) });
      this.blocks = await api("/api/calendar/blocks");
    },
    async delBlock(id) {
      await api("/api/calendar/blocks/" + id, { method: "DELETE" });
      this.blocks = await api("/api/calendar/blocks");
    },
  },
};
</script>
