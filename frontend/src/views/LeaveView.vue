<template>
  <div>
    <h1>Leave</h1>
    <div class="grid cols-2">
      <form class="card" @submit.prevent="apply">
        <h2>Apply</h2>
        <div class="field">
          <label>Type</label>
          <select v-model="form.leave_type_id" required>
            <option value="" disabled>Select</option>
            <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }} ({{ t.days_per_year }}d)</option>
          </select>
        </div>
        <div class="field"><label>Start</label><input v-model="form.start_date" type="date" required /></div>
        <div class="field"><label>End</label><input v-model="form.end_date" type="date" required /></div>
        <div class="field"><label>Reason</label><textarea v-model="form.reason"></textarea></div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit">Submit</button>
      </form>
      <div class="card">
        <h2>Balances</h2>
        <table class="table">
          <thead><tr><th>Type</th><th>Remaining</th></tr></thead>
          <tbody>
            <tr v-for="b in mine" :key="b.id">
              <td>{{ b.leave_type_name }}</td>
              <td>{{ b.remaining }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <h2 style="margin-top:24px">Requests</h2>
    <table class="table">
      <thead>
        <tr><th>Employee</th><th>Type</th><th>Dates</th><th>Days</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in requests" :key="r.id">
          <td>{{ r.employee_name }}</td>
          <td>{{ r.leave_type_name }}</td>
          <td>{{ r.start_date }} - {{ r.end_date }}</td>
          <td>{{ r.days }}</td>
          <td><span class="pill">{{ r.status }}</span></td>
          <td>
            <template v-if="isHr && r.status === 'pending'">
              <button type="button" @click="decide(r, 'approved')">Approve</button>
              <button type="button" class="secondary" @click="decide(r, 'rejected')">Reject</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
import { auth } from "../stores/auth";
export default {
  data: () => ({
    types: [],
    balances: [],
    requests: [],
    error: "",
    form: { leave_type_id: "", start_date: "", end_date: "", reason: "" },
  }),
  computed: {
    isHr() { return auth.user && auth.user.role === "hr"; },
    mine() {
      if (this.isHr) return this.balances;
      const uid = auth.user && auth.user.id;
      return this.balances.filter((b) => !uid || b.employee_id);
    },
  },
  async created() {
    await this.refresh();
  },
  methods: {
    async refresh() {
      this.types = await api("/api/leave/types");
      this.balances = await api("/api/leave/balances");
      this.requests = await api("/api/leave/requests");
    },
    async apply() {
      this.error = "";
      try {
        await api("/api/leave/requests", { method: "POST", body: JSON.stringify(this.form) });
        await this.refresh();
      } catch (e) {
        this.error = e.message || "Could not apply";
      }
    },
    async decide(r, status) {
      await api(`/api/leave/requests/${r.id}/decide`, { method: "POST", body: JSON.stringify({ status }) });
      await this.refresh();
    },
  },
};
</script>
