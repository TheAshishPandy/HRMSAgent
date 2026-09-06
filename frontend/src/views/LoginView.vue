<template>
  <div class="auth-wrap">
    <div class="card auth-card">
      <h1>Sign in</h1>
      <p class="muted">Northstar HRMS</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required autocomplete="username" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit">Continue</button>
      </form>
      <p style="margin-top:16px">No account? <router-link to="/register">Register</router-link></p>
    </div>
  </div>
</template>
<script>
import { login } from "../stores/auth";
export default {
  data: () => ({ email: "", password: "", error: "" }),
  methods: {
    async submit() {
      this.error = "";
      try {
        const u = await login(this.email, this.password);
        const next = this.$route.query.next;
        if (next) this.$router.push(String(next));
        else if (u.role === "super_admin") this.$router.push("/admin");
        else if (u.role === "employee") this.$router.push("/work");
        else this.$router.push(u.role === "hr" ? "/hr" : "/me");
      } catch (e) {
        this.error = "Invalid email or password";
      }
    },
  },
};
</script>
