<template>
  <div style="max-width: 800px; margin: 0 auto;">
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h2 style="margin: 0;">{{ material?.filename }}</n-h2>
      <n-space>
        <n-button @click="$router.push(`/knowledge/${material?.id}`)">查看知识树</n-button>
        <n-button @click="$router.push('/dashboard')">返回</n-button>
      </n-space>
    </n-space>
    <n-card>
      <n-spin :show="loading">
        <n-scrollbar style="max-height: 70vh;">
          <div style="white-space: pre-wrap; font-size: 14px; line-height: 1.8;">
            {{ content }}
          </div>
        </n-scrollbar>
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { materialApi } from '../../api/materials.js'

const route = useRoute()
const message = useMessage()
const material = ref(null)
const loading = ref(true)
const content = ref('')

onMounted(async () => {
  try {
    const res = await materialApi.get(route.params.id)
    material.value = res.data
    content.value = res.data.content_md || '（无内容）'
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})
</script>
