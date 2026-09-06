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
    <table class="table">
      <thead>
        <tr><th>Name</th><th>Email</th><th>Department</th><th>Designation</th><th>Status</th></tr>
      </thead>
      <tbody>
        <tr v-for="e in rows" :key="e.id">
          <td>{{ e.first_name }} {{ e.last_name }}</td>
          <td>{{ e.email }}</td>
          <td>{{ e.department }}</td>
          <td>{{ e.designation }}</td>
          <td><span class="pill">{{ e.status }}</span></td>
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
  },
};
</script>
