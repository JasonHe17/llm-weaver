<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usageApi } from '@/api'
import type { RequestLog } from '@/types'

const loading = ref(false)
const logs = ref<RequestLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await usageApi.getLogs({
      page: currentPage.value,
      page_size: pageSize.value
    })
    logs.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="logs">
    <div class="page-header">
      <h2>请求日志</h2>
    </div>

    <el-card>
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="model" label="模型" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tokens_input" label="输入Tokens" width="120" />
        <el-table-column prop="tokens_output" label="输出Tokens" width="120" />
        <el-table-column prop="cost" label="费用" width="100">
          <template #default="{ row }">
            ${{ row.cost.toFixed(6) }}
          </template>
        </el-table-column>
        <el-table-column prop="latency_ms" label="延迟(ms)" width="100" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_message" class="error-text">{{ row.error_message }}</span>
            <span v-else>-</span>
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
          @change="fetchLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.logs {
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

.error-text {
  color: #F56C6C;
}
</style>