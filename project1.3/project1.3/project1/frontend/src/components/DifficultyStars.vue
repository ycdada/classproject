<template>
  <span :style="{ color: colors[difficulty] || '#999', fontWeight: 'bold' }">
    {{ '★'.repeat(difficulty) }}{{ '☆'.repeat(5 - difficulty) }}
  </span>
</template>
<script setup>
import { DIFFICULTY_COLORS } from '../utils/constants.js'
const props = defineProps({ difficulty: { type: Number, required: true } })
const colors = DIFFICULTY_COLORS
</script>
