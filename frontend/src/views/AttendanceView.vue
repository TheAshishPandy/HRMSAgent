<template>
  <div>
    <h1>Attendance</h1>
    <div class="grid cols-4" style="margin-bottom:20px">
      <div class="card stat"><div class="muted">Present</div><div class="n">{{ board.counts.present || 0 }}</div></div>
      <div class="card stat"><div class="muted">Late</div><div class="n">{{ board.counts.late || 0 }}</div></div>
      <div class="card stat"><div class="muted">Absent</div><div class="n">{{ board.counts.absent || 0 }}</div></div>
      <div class="card stat"><div class="muted">On leave</div><div class="n">{{ board.counts.on_leave || 0 }}</div></div>
    </div>
    <div class="row" style="margin-bottom:16px">
      <button type="button" @click="checkIn">Check in</button>
      <button type="button" class="secondary" @click="checkOut">Check out</button>
      <span v-if="msg" class="muted">{{ msg }}</span>
    </div>
    <table class="table">
      <thead>
        <tr><th>Employee</th><th>Department</th><th>Status</th><th>Check in</th><th>Check out</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in board.rows" :key="r.employee_id">
          <td>{{ r.employee_name }}</td>
          <td>{{ r.department }}</td>
          <td><span class="pill">{{ r.status }}</span></td>
          <td>{{ fmt(r.check_in_at) }}</td>
          <td>{{ fmt(r.check_out_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ board: { counts: {}, rows: [] }, msg: "" }),
  async created() {
    await this.refresh();
  },
  methods: {
    fmt(v) {
      if (!v) return "-";
      return new Date(v).toLocaleTimeString();
    },
    async refresh() {
      this.board = await api("/api/attendance/today");
    },
    async checkIn() {
      this.msg = "";
      try {
        await api("/api/attendance/check-in", { method: "POST" });
        this.msg = "Checked in";
        await this.refresh();
      } catch (e) {
        this.msg = e.message || "Could not check in";
      }
    },
    async checkOut() {
      this.msg = "";
      try {
        await api("/api/attendance/check-out", { method: "POST" });
        this.msg = "Checked out";
        await this.refresh();
      } catch (e) {
        this.msg = e.message || "Could not check out";
      }
    },
  },
};
</script>
