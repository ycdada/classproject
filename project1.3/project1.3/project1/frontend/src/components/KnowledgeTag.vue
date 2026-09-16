<template>
  <n-space wrap>
    <n-tag v-for="kp in points" :key="kp" size="small" :bordered="false" type="info">
      {{ kp }}
    </n-tag>
  </n-space>
</template>
<script setup>
defineProps({ points: { type: Array, default: () => [] } })
</script>
