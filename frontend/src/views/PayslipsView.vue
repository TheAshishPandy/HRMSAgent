<template>
  <div>
    <h1>Payslips</h1>
    <table class="table">
      <thead>
        <tr><th>Period</th><th>Gross</th><th>Tax</th><th>Deductions</th><th>Net</th></tr>
      </thead>
      <tbody>
        <tr v-for="s in slips" :key="s.id">
          <td>{{ s.period }}</td>
          <td>{{ money(s.gross) }}</td>
          <td>{{ money(s.tax) }}</td>
          <td>{{ money(s.other_deductions) }}</td>
          <td>{{ money(s.net) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ slips: [] }),
  async created() {
    this.slips = await api("/api/payroll/payslips");
  },
  methods: {
    money(n) { return Number(n || 0).toLocaleString(); },
  },
};
</script>
