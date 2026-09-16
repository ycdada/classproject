<template>
  <div style="max-width: 1200px; margin: 0 auto;">
    <n-space align="center" style="margin-bottom: 8px;">
      <n-button text @click="$router.push('/dashboard')">
        <template #icon><n-icon><arrow-back-outline /></n-icon></template>
        返回首页
      </n-button>
    </n-space>
    <n-space justify="space-between" style="margin-bottom: 16px;">
      <n-h2 style="margin: 0;">知识树 — {{ materialName }}</n-h2>
      <n-space>
        <n-button type="primary" :loading="extracting" @click="extract" v-if="!nodes.length">
          提取知识树
        </n-button>
        <n-button @click="extract" :loading="extracting" v-else>重新提取</n-button>
        <n-button type="info" @click="goGenerateExam" :disabled="!selectedNodes.length">
          用选中知识点组卷 ({{ selectedNodes.length }})
        </n-button>
      </n-space>
    </n-space>

    <n-spin :show="loading">
      <n-grid cols="2" :x-gap="12">
        <n-grid-item>
          <n-card title="知识点结构" size="small">
            <KnowledgeTreePanel :nodes="nodes" @update:checked-keys="onCheck" />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="节点详情" size="small" v-if="selectedNode">
            <n-descriptions :column="1" bordered size="small">
              <n-descriptions-item label="名称">{{ selectedNode.name }}</n-descriptions-item>
              <n-descriptions-item label="类型">{{ selectedNode.node_type }}</n-descriptions-item>
              <n-descriptions-item label="定义">{{ selectedNode.definition || '无' }}</n-descriptions-item>
              <n-descriptions-item label="术语">{{ (selectedNode.key_terms || []).join(', ') || '无' }}</n-descriptions-item>
              <n-descriptions-item label="重点">{{ selectedNode.teaching_emphasis || '无' }}</n-descriptions-item>
            </n-descriptions>
          </n-card>
          <n-empty v-else description="点击左侧节点查看详情" style="margin-top: 60px;" />
        </n-grid-item>
      </n-grid>
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { knowledgeApi } from '../../api/knowledge.js'
import { materialApi } from '../../api/materials.js'
import KnowledgeTreePanel from '../../components/KnowledgeTreePanel.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const materialId = parseInt(route.params.materialId)
const materialName = ref('')
const nodes = ref([])
const selectedNodes = ref([])
const selectedNode = ref(null)
const loading = ref(false)
const extracting = ref(false)

onMounted(async () => {
  try {
    const mat = await materialApi.get(materialId)
    materialName.value = mat.data.filename
    const res = await knowledgeApi.getTree(materialId)
    nodes.value = res.data
  } catch (e) { /* no tree yet */ }
})

async function extract() {
  extracting.value = true
  try {
    await knowledgeApi.extract(materialId)
    message.success('知识树提取完成')
    const res = await knowledgeApi.getTree(materialId)
    nodes.value = res.data
  } catch (e) {
    message.error('提取失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    extracting.value = false
  }
}

function onCheck(keys) {
  selectedNodes.value = keys
}

function goGenerateExam() {
  router.push({
    path: '/exams/create',
    query: { nodeIds: selectedNodes.value.join(',') }
  })
}
</script>
