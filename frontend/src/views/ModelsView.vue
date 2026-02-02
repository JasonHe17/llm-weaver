<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { modelsApi } from '@/api'
import type { Model } from '@/types'

const loading = ref(false)
const models = ref<Model[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const fetchModels = async () => {
  loading.value = true
  try {
    const response = await modelsApi.getModels({
      page: currentPage.value,
      page_size: pageSize.value
    })
    models.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    console.error('Failed to fetch models:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<template>
  <div class="models">
    <div class="page-header">
      <h2>模型管理</h2>
    </div>

    <el-card>
      <el-table :data="models" v-loading="loading" stripe>
        <el-table-column prop="id" label="模型ID" min-width="180" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="provider" label="提供商" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '活跃' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="context_length" label="上下文长度" width="120">
          <template #default="{ row }">
            {{ row.context_length?.toLocaleString() || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="fetchModels"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.models {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-weight: 500;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>