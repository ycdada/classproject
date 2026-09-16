<template>
  <div class="search-card">
    <div class="search-card__header">🔍 找到 {{ data.count }} 道相关题目</div>
    <div v-for="r in data.results" :key="r.id" class="search-card__item">
      <n-space align="center">
        <n-tag :type="typeColor(r.question?.type)" size="small">
          {{ typeLabel(r.question?.type) }}
        </n-tag>
        <DifficultyStars :difficulty="r.question?.difficulty || 3" />
      </n-space>
      <p class="search-card__content">{{ truncate(r.question?.content || r.document, 80) }}</p>
      <n-button size="tiny" @click="$emit('addToExam', r.id)">加入试卷</n-button>
    </div>
  </div>
</template>

<script setup>
import DifficultyStars from './DifficultyStars.vue'

defineProps({ data: Object })
defineEmits(['addToExam'])

function typeLabel(type) {
  return { choice: '选择', fill: '填空', tf: '判断', short_answer: '简答', code: '编程' }[type] || type
}

function typeColor(type) {
  return { choice: 'info', fill: 'warning', tf: 'success', short_answer: 'default', code: 'error' }[type] || 'default'
}

function truncate(text, len) {
  return text && text.length > len ? text.slice(0, len) + '...' : text
}
</script>

<style scoped>
.search-card__header {
  font-weight: 600;
  margin-bottom: 8px;
}
.search-card__item {
  border-top: 1px solid #eee;
  padding: 8px 0;
}
.search-card__content {
  font-size: 13px;
  color: #666;
  margin: 4px 0;
}
</style>
