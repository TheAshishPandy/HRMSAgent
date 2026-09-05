<template>
  <div class="auth-wrap">
    <div class="card auth-card">
      <h1>Create account</h1>
      <form @submit.prevent="submit">
        <div class="field">
          <label for="name">Name</label>
          <input id="name" v-model="name" required />
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required minlength="6" />
        </div>
        <div class="field">
          <label for="role">Role</label>
          <select id="role" v-model="role">
            <option value="candidate">Candidate</option>
            <option value="hr">HR (only if none exists yet)</option>
          </select>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit">Register</button>
      </form>
      <p style="margin-top:16px"><router-link to="/login">Back to sign in</router-link></p>
    </div>
  </div>
</template>
<script>
import { register } from "../stores/auth";
export default {
  data: () => ({ name: "", email: "", password: "", role: "candidate", error: "" }),
  methods: {
    async submit() {
      this.error = "";
      try {
        const u = await register({
          name: this.name,
          email: this.email,
          password: this.password,
          role: this.role,
        });
        this.$router.push(u.role === "hr" ? "/hr" : "/me");
      } catch (e) {
        this.error = "Could not register";
      }
    },
  },
};
</script>
