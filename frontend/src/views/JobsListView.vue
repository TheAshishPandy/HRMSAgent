<template>
  <div>
    <div class="row" style="justify-content:space-between">
      <h1>Jobs</h1>
      <router-link to="/hr/jobs/new"><button type="button">New job</button></router-link>
    </div>
    <table class="table">
      <thead><tr><th>Title</th><th>Team</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <tr v-for="j in jobs" :key="j.id">
          <td>{{ j.title }}</td>
          <td>{{ j.team }}</td>
          <td><span class="pill">{{ j.status }}</span></td>
          <td class="row">
            <router-link :to="'/hr/jobs/' + j.id + '/edit'">Edit</router-link>
            <router-link :to="'/hr/jobs/' + j.id + '/pipeline'">Pipeline</router-link>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ jobs: [] }),
  async created() {
    this.jobs = await api("/api/jobs");
  },
};
</script>
