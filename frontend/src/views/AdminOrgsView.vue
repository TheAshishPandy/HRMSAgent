<template>
  <div>
    <div class="row" style="justify-content:space-between">
      <h1>Organizations</h1>
      <button type="button" @click="show = !show">New organization</button>
    </div>
    <form v-if="show" class="card" style="margin:16px 0" @submit.prevent="create">
      <div class="grid cols-2">
        <div class="field"><label>Name</label><input v-model="form.name" required /></div>
        <div class="field"><label>Slug</label><input v-model="form.slug" required /></div>
        <div class="field">
          <label>Theme</label>
          <select v-model="form.theme_key">
            <option v-for="t in themes" :key="t.key" :value="t.key">{{ t.name }}</option>
          </select>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">Create</button>
    </form>
    <table class="table">
      <thead>
        <tr><th>Name</th><th>Slug</th><th>Theme</th><th>Layout</th><th>Status</th></tr>
      </thead>
      <tbody>
        <tr v-for="o in orgs" :key="o.id">
          <td>{{ o.name }}</td>
          <td>{{ o.slug }}</td>
          <td>
            <select :value="o.theme_key" @change="setTheme(o, $event.target.value)">
              <option v-for="t in themes" :key="t.key" :value="t.key">{{ t.name }}</option>
            </select>
          </td>
          <td>{{ o.layout_key }}</td>
          <td><span class="pill">{{ o.status }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({
    orgs: [],
    themes: [],
    show: false,
    error: "",
    form: { name: "", slug: "", theme_key: "corporate_blue" },
  }),
  async created() {
    this.themes = await api("/api/orgs/themes");
    this.orgs = await api("/api/orgs");
  },
  methods: {
    async create() {
      this.error = "";
      try {
        const o = await api("/api/orgs", { method: "POST", body: JSON.stringify(this.form) });
        this.orgs.push(o);
        this.show = false;
      } catch (err) {
        this.error = err.message || "Could not create organization";
      }
    },
    async setTheme(o, theme_key) {
      const updated = await api(`/api/orgs/${o.id}`, { method: "PATCH", body: JSON.stringify({ theme_key }) });
      Object.assign(o, updated);
    },
  },
};
</script>
