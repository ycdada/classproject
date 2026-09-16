<template>
  <n-tree
    :data="treeData"
    checkable
    selectable
    :checked-keys="checkedKeys"
    :expanded-keys="expandedKeys"
    key-field="id"
    label-field="name"
    children-field="children"
    @update:checked-keys="onCheck"
    @update:expanded-keys="onExpand"
  />
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ nodes: { type: Array, default: () => [] } })
const emit = defineEmits(['update:checkedKeys'])

const treeData = ref([])
const expandedKeys = ref([])
const checkedKeys = ref([])

watch(() => props.nodes, (val) => {
  treeData.value = val || []
  expandedKeys.value = (val || []).map(n => n.id)
  checkedKeys.value = []
}, { immediate: true })

function onCheck(keys) {
  checkedKeys.value = keys
  emit('update:checkedKeys', keys)
}

function onExpand(keys) {
  expandedKeys.value = keys
}
</script>
