<template>
  <div>
    <h1>Design studio</h1>
    <div class="field">
      <label>Organization</label>
      <select v-model="orgId" @change="loadOrg">
        <option value="">Select</option>
        <option v-for="o in orgs" :key="o.id" :value="o.id">{{ o.name }}</option>
      </select>
    </div>
    <form v-if="org" class="grid cols-2" @submit.prevent="save">
      <div class="card">
        <h2>Theme</h2>
        <div class="field">
          <label>Preset</label>
          <select v-model="form.theme_key">
            <option v-for="t in themes" :key="t.key" :value="t.key">{{ t.name }}</option>
          </select>
        </div>
        <div class="field"><label>Primary</label><input v-model="form.theme_overrides.primary" type="color" /></div>
        <div class="field"><label>Accent</label><input v-model="form.theme_overrides.accent" type="color" /></div>
        <div class="field"><label>Background</label><input v-model="form.theme_overrides.background" type="color" /></div>
        <div class="field"><label>Text</label><input v-model="form.theme_overrides.text" type="color" /></div>
        <div class="field"><label>Radius</label><input v-model="form.theme_overrides.radius" placeholder="12px" /></div>
      </div>
      <div class="card">
        <h2>Layout and branding</h2>
        <div class="field">
          <label>Layout</label>
          <select v-model="form.layout_key">
            <option v-for="l in layouts" :key="l.key" :value="l.key">{{ l.name }}</option>
          </select>
        </div>
        <div class="field"><label>Organization name</label><input v-model="form.name" /></div>
        <div class="field"><label>Logo URL</label><input v-model="form.logo_url" /></div>
        <div class="field">
          <label>Modules</label>
          <label v-for="m in modules" :key="m" style="font-weight:400;margin:4px 0">
            <input type="checkbox" :value="m" v-model="form.modules" /> {{ m }}
          </label>
        </div>
      </div>
      <div class="card">
        <h2>Preview</h2>
        <p>{{ form.name }} · {{ form.theme_key }} · {{ form.layout_key }}</p>
        <div class="row">
          <span class="swatch" :style="{ background: form.theme_overrides.primary || previewTheme.primary }"></span>
          <span class="swatch" :style="{ background: form.theme_overrides.accent || previewTheme.accent }"></span>
          <span class="swatch" :style="{ background: form.theme_overrides.background || previewTheme.background }"></span>
        </div>
        <p v-if="msg" class="muted">{{ msg }}</p>
        <button type="submit">Save studio</button>
      </div>
    </form>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({
    orgs: [],
    themes: [],
    layouts: [],
    modules: [],
    orgId: "",
    org: null,
    msg: "",
    form: { name: "", theme_key: "corporate_blue", layout_key: "classic_sidebar", logo_url: "", modules: [], theme_overrides: {} },
  }),
  computed: {
    previewTheme() {
      return this.themes.find((t) => t.key === this.form.theme_key) || {};
    },
  },
  async created() {
    this.themes = await api("/api/orgs/themes");
    this.layouts = await api("/api/orgs/layouts");
    this.modules = await api("/api/orgs/modules");
    this.orgs = await api("/api/orgs");
    if (this.orgs.length) {
      this.orgId = this.orgs[0].id;
      this.loadOrg();
    }
  },
  methods: {
    loadOrg() {
      this.org = this.orgs.find((o) => o.id === this.orgId) || null;
      if (!this.org) return;
      this.form = {
        name: this.org.name,
        theme_key: this.org.theme_key,
        layout_key: this.org.layout_key,
        logo_url: this.org.logo_url || "",
        modules: [...(this.org.modules || [])],
        theme_overrides: { ...(this.org.theme_overrides || {}) },
      };
    },
    async save() {
      this.msg = "";
      const updated = await api(`/api/orgs/${this.org.id}`, { method: "PATCH", body: JSON.stringify(this.form) });
      Object.assign(this.org, updated);
      this.msg = "Saved";
    },
  },
};
</script>
