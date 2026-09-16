<template>
  <div style="max-width: 700px; margin: 0 auto;">
    <n-space align="center" style="margin-bottom: 16px;">
      <n-button text @click="$router.push('/dashboard')">
        <template #icon><n-icon><arrow-back-outline /></n-icon></template>
        返回首页
      </n-button>
    </n-space>
    <n-h2 style="margin-bottom: 16px;">上传教学材料</n-h2>

    <!-- 拖拽上传区域 -->
    <div
      class="drop-zone"
      :class="{ 'drop-active': dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="handleDrop"
    >
      <n-icon :size="48" color="#0E7C86"><cloud-upload-outline /></n-icon>
      <p style="margin:12px 0 4px;font-size:15px;font-weight:500;">拖拽文件到此处上传</p>
      <p style="color:#9ca3af;font-size:13px;">支持 .pptx .docx .pdf .md，可一次拖入多个文件</p>
      <n-button style="margin-top:12px;" @click="triggerFileInput" size="small" type="primary" ghost>
        或点击选择文件
      </n-button>
      <input ref="fileInput" type="file" multiple accept=".pptx,.docx,.pdf,.md" style="display:none;" @change="handleFileSelect" />
    </div>

    <!-- 已选择的文件列表 -->
    <n-card v-if="files.length" title="待上传文件" size="small" style="margin-top:12px;">
      <template #header-extra>
        <n-tag type="info" size="small">{{ files.length }} 个</n-tag>
      </template>
      <div v-for="(f, idx) in files" :key="idx" class="file-row">
        <span class="file-name">{{ f.name }}</span>
        <span class="file-size">{{ formatSize(f.size) }}</span>
        <n-button text size="tiny" type="error" @click="removeFile(idx)">移除</n-button>
      </div>
      <n-divider style="margin:8px 0;" />
      <n-form-item label="统一章节号（可选）" label-placement="left">
        <n-input-number v-model:value="chapter" :min="1" placeholder="如: 5" size="small" style="width:120px;" />
      </n-form-item>
      <n-button type="primary" :loading="uploading" @click="uploadAll" block>
        {{ uploading ? `上传中...` : `一键上传 ${files.length} 个文件` }}
      </n-button>
    </n-card>

    <!-- 上传结果 -->
    <n-space v-if="results.length" vertical style="margin-top:12px;">
      <n-alert v-for="r in results" :key="r.filename" :type="r.error ? 'error' : 'success'">
        {{ r.filename }} — {{ r.error ? '失败: ' + r.error : `解析完成 (${r.page_count || '?'}页)` }}
      </n-alert>
      <n-space>
        <n-button @click="clearAndContinue">继续上传</n-button>
        <n-button type="primary" @click="$router.push('/dashboard')">返回首页</n-button>
      </n-space>
    </n-space>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import { CloudUploadOutline, ArrowBackOutline } from '@vicons/ionicons5'
import { materialApi } from '../../api/materials.js'

const message = useMessage()
const fileInput = ref(null)
const dragging = ref(false)
const files = ref([])
const chapter = ref(null)
const uploading = ref(false)
const results = ref([])

function triggerFileInput() { fileInput.value?.click() }

function handleDrop(e) {
  dragging.value = false
  addFiles(e.dataTransfer.files)
}

function handleFileSelect(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function addFiles(fileList) {
  for (const f of fileList) {
    const ext = f.name.split('.').pop()?.toLowerCase()
    if (['pptx', 'docx', 'pdf', 'md'].includes(ext) && !files.value.find(x => x.name === f.name && x.size === f.size)) {
      files.value.push(f)
    }
  }
}

function removeFile(idx) { files.value.splice(idx, 1) }
function formatSize(bytes) {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

async function uploadAll() {
  uploading.value = true
  results.value = []
  for (const f of files.value) {
    try {
      const fd = new FormData()
      fd.append('file', f)
      if (chapter.value) fd.append('chapter', chapter.value)
      const res = await materialApi.upload(fd)
      results.value.push(res.data)
    } catch (e) {
      results.value.push({ filename: f.name, error: e.response?.data?.detail || e.message })
    }
  }
  uploading.value = false
  files.value = []
  if (results.value.every(r => !r.error)) {
    message.success(`${results.value.length} 个文件全部上传成功`)
  }
}

function clearAndContinue() {
  results.value = []
  chapter.value = null
}
</script>

<style scoped>
.drop-zone {
  border:2px dashed #d1d5db; border-radius:12px; padding:40px 24px; text-align:center;
  transition:all .2s; background:#fafafa; cursor:pointer;
}
.drop-zone.drop-active { border-color:#0E7C86; background:#E9F4F5; }
.file-row { display:flex; align-items:center; gap:12px; padding:6px 0; border-bottom:1px solid #f0f0f0; }
.file-row:last-child { border-bottom:none; }
.file-name { flex:1; font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.file-size { font-size:12px; color:#9ca3af; }
</style>
