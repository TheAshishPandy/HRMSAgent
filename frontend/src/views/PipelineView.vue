<template>
  <div>
    <h1>Pipeline</h1>
    <div class="row" style="margin-bottom:12px">
      <button class="ghost" :class="{ secondary: tab==='board' }" @click="tab='board'">Board</button>
      <button class="ghost" @click="tab='other'">Hired / Withdrawn</button>
    </div>
    <PipelineBoard v-if="tab==='board'" :apps="apps">
      <template #actions="{ app }">
        <router-link :to="'/hr/applications/' + app.id">Open</router-link>
      </template>
    </PipelineBoard>
    <table v-else class="table">
      <tr v-for="a in others" :key="a.id">
        <td>{{ a.candidate_name }}</td>
        <td><span class="pill">{{ a.status }}</span></td>
        <td><router-link :to="'/hr/applications/' + a.id">Open</router-link></td>
      </tr>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
import PipelineBoard from "../components/PipelineBoard.vue";
export default {
  components: { PipelineBoard },
  data: () => ({ apps: [], tab: "board" }),
  computed: {
    others() { return this.apps.filter((a) => a.status === "hired" || a.status === "withdrawn"); },
  },
  async created() {
    this.apps = await api("/api/applications?job_id=" + this.$route.params.id);
  },
};
</script>
