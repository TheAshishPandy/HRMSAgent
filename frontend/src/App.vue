<template>
  <AppShell v-if="authedLayout">
    <router-view />
  </AppShell>
  <router-view v-else />
</template>
<script>
import AppShell from "./components/AppShell.vue";
export default {
  components: { AppShell },
  computed: {
    authedLayout() {
      const p = this.$route.path;
      return p.startsWith("/hr") || p.startsWith("/me") || p.startsWith("/admin");
    },
  },
};
</script>
