<template>
  <n-card :title="'第' + (index + 1) + '题 (' + question.score + '分)'" size="small">
    <p>{{ question.content }}</p>
    <slot />
  </n-card>
</template>
<script setup>
defineProps({ question: Object, index: Number })
</script>
