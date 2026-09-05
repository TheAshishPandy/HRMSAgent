<template>
  <div>
    <h1>My applications</h1>
    <table class="table">
      <tr v-for="a in apps" :key="a.id">
        <td>{{ a.job_title }}</td>
        <td><span class="pill">{{ a.status }}</span></td>
        <td><router-link :to="'/me/applications/' + a.id">Open</router-link></td>
      </tr>
    </table>
    <p><router-link to="/">Browse open roles</router-link></p>
    <button class="ghost" type="button" @click="exp">Export my data</button>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({ apps: [] }),
  async created() {
    this.apps = await api("/api/applications");
  },
  methods: {
    async exp() {
      const data = await api("/api/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "my-data.json";
      a.click();
    },
  },
};
</script>
