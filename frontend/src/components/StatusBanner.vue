<template>
  <div v-if="text" class="banner" role="status">{{ text }}</div>
</template>
<script>
export default {
  props: { text: { type: String, default: "" } },
};
</script>
