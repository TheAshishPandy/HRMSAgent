<template>
  <AppShell v-if="authedLayout">
    <router-view />
  </AppShell>
  <router-view v-else />
  <SmartChat />
</template>
<script>
import AppShell from "./components/AppShell.vue";
import SmartChat from "./components/SmartChat.vue";
export default {
  components: { AppShell, SmartChat },
  computed: {
    authedLayout() {
      const p = this.$route.path;
      return p.startsWith("/hr") || p.startsWith("/me") || p.startsWith("/admin") || p.startsWith("/work");
    },
  },
};
</script>
