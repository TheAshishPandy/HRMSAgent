<template>
  <div>
    <div class="row" style="justify-content:space-between">
      <h1>Employees</h1>
      <button type="button" @click="show = !show">Add employee</button>
    </div>
    <form v-if="show" class="card" style="margin:16px 0" @submit.prevent="create">
      <div class="grid cols-2">
        <div class="field"><label>First name</label><input v-model="form.first_name" required /></div>
        <div class="field"><label>Last name</label><input v-model="form.last_name" required /></div>
        <div class="field"><label>Email</label><input v-model="form.email" type="email" required /></div>
        <div class="field"><label>Department</label><input v-model="form.department" /></div>
        <div class="field"><label>Designation</label><input v-model="form.designation" /></div>
        <div class="field"><label>Joining date</label><input v-model="form.joining_date" type="date" /></div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">Save</button>
    </form>
    <form v-if="offboarding" class="card" style="margin:16px 0" @submit.prevent="confirmOffboard">
      <h3 style="margin-top:0">Offboard {{ offboarding.first_name }} {{ offboarding.last_name }}</h3>
      <div class="grid cols-2">
        <div class="field"><label>Exit date</label><input v-model="exit.exit_date" type="date" required /></div>
        <div class="field"><label>Reason</label><input v-model="exit.reason" placeholder="Resigned / contract end" required /></div>
      </div>
      <p v-if="offError" class="error">{{ offError }}</p>
      <button type="submit">Confirm exit</button>
      <button type="button" class="ghost" @click="offboarding = null">Cancel</button>
    </form>
    <table class="table">
      <thead>
        <tr><th>Name</th><th>Email</th><th>Department</th><th>Designation</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="e in rows" :key="e.id">
          <td>{{ e.first_name }} {{ e.last_name }}</td>
          <td>{{ e.email }}</td>
          <td>{{ e.department }}</td>
          <td>{{ e.designation }}</td>
          <td>
            <span class="pill">{{ e.status }}</span>
            <span v-if="e.exit_date" class="muted"><br />Exit {{ e.exit_date }}</span>
          </td>
          <td>
            <button v-if="e.status === 'active'" type="button" class="ghost" @click="beginOffboard(e)">Offboard</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import { api } from "../api";
export default {
  data: () => ({
    rows: [],
    show: false,
    error: "",
    offError: "",
    offboarding: null,
    exit: { exit_date: "", reason: "" },
    form: { first_name: "", last_name: "", email: "", department: "", designation: "", joining_date: "", status: "active" },
  }),
  async created() {
    this.rows = await api("/api/employees");
  },
  methods: {
    async create() {
      this.error = "";
      try {
        const e = await api("/api/employees", { method: "POST", body: JSON.stringify(this.form) });
        this.rows.push(e);
        this.show = false;
      } catch (err) {
        this.error = err.message || "Could not create employee";
      }
    },
    beginOffboard(e) {
      this.offboarding = e;
      this.offError = "";
      this.exit = { exit_date: new Date().toISOString().slice(0, 10), reason: "" };
    },
    async confirmOffboard() {
      this.offError = "";
      try {
        const updated = await api(`/api/onboarding/employees/${this.offboarding.id}/offboard`, {
          method: "POST",
          body: JSON.stringify(this.exit),
        });
        const idx = this.rows.findIndex((r) => r.id === this.offboarding.id);
        if (idx >= 0) {
          this.rows[idx] = { ...this.rows[idx], ...updated };
        }
        this.offboarding = null;
      } catch (err) {
        this.offError = err.message || "Could not offboard";
      }
    },
  },
};
</script>
