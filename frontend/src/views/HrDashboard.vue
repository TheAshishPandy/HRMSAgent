<template>
  <div>
    <h1>Dashboard</h1>
    <div class="grid cols-4">
      <div class="card stat"><div class="muted">Open jobs</div><div class="n">{{ d.open_jobs }}</div></div>
      <div class="card stat"><div class="muted">Applied</div><div class="n">{{ d.pipeline.applied || 0 }}</div></div>
      <div class="card stat"><div class="muted">Interviews (7d)</div><div class="n">{{ d.upcoming_interviews }}</div></div>
      <div class="card stat"><div class="muted">Employees</div><div class="n">{{ d.employees || 0 }}</div></div>
    </div>
    <p style="margin-top:24px"><router-link to="/hr/attendance">Attendance</router-link> · <router-link to="/hr/leave">Leave</router-link> · <router-link to="/hr/payroll">Payroll</router-link> · <router-link to="/hr/employees">People directory</router-link> · <router-link to="/hr/jobs/new">Create a job</router-link></p>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ d: { open_jobs: 0, pipeline: {}, upcoming_interviews: 0, unread: 0, employees: 0 } }),
  async created() {
    this.d = await api("/api/hr/dashboard");
  },
};
</script>
