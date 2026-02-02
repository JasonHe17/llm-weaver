<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usageApi } from '@/api'
import type { UsageStats } from '@/types'

const loading = ref(false)
const stats = ref<UsageStats | null>(null)
const timeRange = ref(7)

const fetchStats = async () => {
  loading.value = true
  try {
    const response = await usageApi.getStats({ days: timeRange.value })
    stats.value = response.data.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<template>
  <div class="usage">
    <div class="page-header">
      <h2>用量统计</h2>
      <el-radio-group v-model="timeRange" @change="fetchStats">
        <el-radio-button :label="7">近7天</el-radio-button>
        <el-radio-button :label="30">近30天</el-radio-button>
        <el-radio-button :label="90">近90天</el-radio-button>
      </el-radio-group>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card v-loading="loading">
          <div class="stat-item">
            <div class="stat-label">总请求数</div>
            <div class="stat-value">{{ stats?.total_requests || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card v-loading="loading">
          <div class="stat-item">
            <div class="stat-label">总Tokens</div>
            <div class="stat-value">{{ stats?.total_tokens?.toLocaleString() || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card v-loading="loading">
          <div class="stat-item">
            <div class="stat-label">总费用</div>
            <div class="stat-value">${{ (stats?.total_cost || 0).toFixed(4) }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="table-card" v-loading="loading">
      <h3>模型使用详情</h3>
      <el-table :data="stats?.requests_by_model || []" stripe>
        <el-table-column prop="model" label="模型" />
        <el-table-column prop="count" label="请求数" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.usage {
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

.stat-item {
  text-align: center;
  padding: 20px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.table-card {
  margin-top: 20px;
}

.table-card h3 {
  margin-bottom: 20px;
  font-weight: 500;
}
</style>