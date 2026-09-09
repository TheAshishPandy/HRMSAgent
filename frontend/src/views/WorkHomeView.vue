<template>
  <div>
    <h1>My work</h1>
    <div class="row" style="margin-bottom:16px">
      <button type="button" @click="checkIn">Check in</button>
      <button type="button" class="secondary" @click="checkOut">Check out</button>
      <span class="muted">{{ msg }}</span>
    </div>
    <div class="grid cols-2">
      <div class="card">
        <h2>Today</h2>
        <p v-if="today">{{ today.status }} {{ today.check_in_at ? "in " + fmt(today.check_in_at) : "" }}</p>
        <p v-else class="muted">No check-in yet</p>
      </div>
      <div class="card">
        <h2>Leave balance</h2>
        <p v-for="b in balances" :key="b.id">{{ b.leave_type_name }}: {{ b.remaining }}</p>
        <p v-if="!balances.length" class="muted">No leave types assigned yet</p>
      </div>
      <div v-if="onboarding" class="card">
        <h2>Onboarding</h2>
        <p>{{ onboarding.completed_tasks }}/{{ onboarding.tasks_total }} tasks · {{ onboarding.status }}</p>
        <p class="muted">{{ onboarding.job_title }} · joins {{ onboarding.joining_date || "TBD" }}</p>
        <router-link to="/work/onboarding">Open checklist</router-link>
      </div>
      <div class="card">
        <h2>Inbox</h2>
        <p class="muted">Welcome notes, offers, and exit notices land here.</p>
        <router-link to="/work/inbox">Open inbox</router-link>
      </div>
    </div>
    <p style="margin-top:24px"><router-link to="/work/leave">Apply for leave</router-link> · <router-link to="/work/payslips">Payslips</router-link></p>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ today: null, balances: [], msg: "", onboarding: null }),
  async created() {
    try {
      const rows = await api("/api/attendance/me");
      const day = new Date().toISOString().slice(0, 10);
      this.today = rows.find((r) => r.work_date === day) || null;
    } catch (e) {
      this.msg = e.message || "Could not load attendance";
    }
    try {
      this.balances = await api("/api/leave/balances");
    } catch (e) {
      this.balances = [];
    }
    try {
      this.onboarding = await api("/api/onboarding/me");
    } catch (e) {
      this.onboarding = null;
    }
  },
  methods: {
    fmt(v) { return v ? new Date(v).toLocaleTimeString() : ""; },
    async checkIn() {
      try {
        this.today = await api("/api/attendance/check-in", { method: "POST" });
        this.msg = "Checked in";
      } catch (e) {
        this.msg = e.message || "Could not check in";
      }
    },
    async checkOut() {
      try {
        this.today = await api("/api/attendance/check-out", { method: "POST" });
        this.msg = "Checked out";
      } catch (e) {
        this.msg = e.message || "Could not check out";
      }
    },
  },
};
</script>
