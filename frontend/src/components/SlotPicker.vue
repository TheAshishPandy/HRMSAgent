<template>
  <div class="grid">
    <button
      v-for="slot in slots"
      :key="slot.start_at"
      class="secondary"
      :class="{ off: isWeekend(slot.start_at) }"
      :disabled="isWeekend(slot.start_at)"
      type="button"
      @click="$emit('select', slot)"
    >
      {{ label(slot.start_at) }}
    </button>
  </div>
</template>
<script>
export default {
  props: { slots: { type: Array, default: () => [] } },
  emits: ["select"],
  methods: {
    isWeekend(iso) {
      const d = new Date(iso);
      const day = d.getUTCDay();
      return day === 0 || day === 6;
    },
    label(iso) {
      const d = new Date(iso);
      return d.toUTCString().replace(" GMT", " UTC");
    },
  },
};
</script>
