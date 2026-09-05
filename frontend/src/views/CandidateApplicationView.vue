<template>
  <div v-if="app">
    <h1>{{ app.job_title }}</h1>
    <p class="pill">{{ app.status }}</p>
    <div v-for="iv in app.interviews" :key="iv.id" class="card" style="margin-top:12px">
      <p>{{ iv.start_at }} · {{ iv.status }}</p>
      <button v-if="iv.status === 'proposed'" type="button" @click="confirm(iv.id)">Confirm interview</button>
    </div>
    <div v-if="app.status === 'offer'" class="row" style="margin-top:16px">
      <button type="button" @click="act('accept-offer')">Accept offer</button>
      <button class="danger" type="button" @click="act('decline-offer')">Decline</button>
    </div>
    <button v-if="app.status !== 'hired' && app.status !== 'withdrawn'" class="ghost" type="button" @click="act('withdraw')">Withdraw</button>
    <h2 style="margin-top:24px">Open weekday slots</h2>
    <SlotPicker :slots="slots" @select="pick" />
  </div>
</template>
<script>
import { api } from "../api";
import SlotPicker from "../components/SlotPicker.vue";
export default {
  components: { SlotPicker },
  data: () => ({ app: null, slots: [] }),
  async created() {
    this.app = await api("/api/applications/" + this.$route.params.id);
    if (this.app.hr_id) {
      const from = new Date().toISOString();
      const to = new Date(Date.now() + 14 * 86400000).toISOString();
      this.slots = await api(`/api/calendar/slots?hr_id=${this.app.hr_id}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    }
  },
  methods: {
    async confirm(id) {
      await api("/api/interviews/" + id + "/confirm", { method: "POST" });
      this.app = await api("/api/applications/" + this.app.id);
    },
    async act(kind) {
      await api("/api/applications/" + this.app.id + "/" + kind, { method: "POST" });
      this.app = await api("/api/applications/" + this.app.id);
    },
    pick() {},
  },
};
</script>
