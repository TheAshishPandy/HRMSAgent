<template>
  <div>
    <h1>Payroll</h1>
    <div class="grid cols-4" style="margin-bottom:20px">
      <div class="card stat"><div class="muted">Gross</div><div class="n">{{ money(summary.gross) }}</div></div>
      <div class="card stat"><div class="muted">Net</div><div class="n">{{ money(summary.net) }}</div></div>
      <div class="card stat"><div class="muted">Tax</div><div class="n">{{ money(summary.tax) }}</div></div>
      <div class="card stat"><div class="muted">Pending runs</div><div class="n">{{ summary.pending_runs }}</div></div>
    </div>
    <form class="card" style="margin-bottom:20px" @submit.prevent="createRun">
      <div class="row">
        <div class="field" style="margin:0">
          <label>Period</label>
          <input v-model="period" placeholder="YYYY-MM" required />
        </div>
        <button type="submit">Create run</button>
        <span class="muted">{{ msg }}</span>
      </div>
    </form>
    <h2>Runs</h2>
    <table class="table">
      <thead>
        <tr><th>Period</th><th>Status</th><th>Gross</th><th>Net</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in runs" :key="r.id">
          <td>{{ r.period }}</td>
          <td><span class="pill">{{ r.status }}</span></td>
          <td>{{ money(r.gross) }}</td>
          <td>{{ money(r.net) }}</td>
          <td>
            <button v-if="r.status === 'draft'" type="button" @click="process(r)">Process</button>
            <button type="button" class="secondary" @click="open(r)">Slips</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="detail" class="card" style="margin-top:20px">
      <h2>Payslips {{ detail.period }}</h2>
      <table class="table">
        <thead><tr><th>Employee</th><th>Gross</th><th>Tax</th><th>Net</th></tr></thead>
        <tbody>
          <tr v-for="s in detail.payslips" :key="s.id">
            <td>{{ s.employee_name }}</td>
            <td>{{ money(s.gross) }}</td>
            <td>{{ money(s.tax) }}</td>
            <td>{{ money(s.net) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <h2 style="margin-top:24px">Salary structures</h2>
    <table class="table">
      <thead><tr><th>Employee</th><th>Basic</th><th>HRA</th><th>Allowance</th><th>Tax %</th></tr></thead>
      <tbody>
        <tr v-for="s in structures" :key="s.id">
          <td>{{ s.employee_name }}</td>
          <td>{{ money(s.basic) }}</td>
          <td>{{ money(s.hra) }}</td>
          <td>{{ money(s.allowance) }}</td>
          <td>{{ s.tax_percent }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ summary: { gross: 0, net: 0, tax: 0, pending_runs: 0 }, runs: [], structures: [], detail: null, period: "2026-09", msg: "" }),
  async created() {
    await this.refresh();
  },
  methods: {
    money(n) { return Number(n || 0).toLocaleString(); },
    async refresh() {
      this.summary = await api("/api/payroll/summary");
      this.runs = await api("/api/payroll/runs");
      this.structures = await api("/api/payroll/structures");
    },
    async createRun() {
      this.msg = "";
      try {
        await api("/api/payroll/runs", { method: "POST", body: JSON.stringify({ period: this.period }) });
        await this.refresh();
      } catch (e) {
        this.msg = e.message || "Could not create run";
      }
    },
    async process(r) {
      await api(`/api/payroll/runs/${r.id}/process`, { method: "POST" });
      await this.refresh();
    },
    async open(r) {
      this.detail = await api(`/api/payroll/runs/${r.id}`);
    },
  },
};
</script>
