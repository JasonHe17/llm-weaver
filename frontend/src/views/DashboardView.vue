<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { usageApi } from '@/api'
import type { UsageStats } from '@/types'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
])

const loading = ref(false)
const stats = ref<UsageStats | null>(null)

// 请求趋势图表配置
const requestTrendOption = ref({
  title: {
    text: '请求趋势 (近7天)',
    left: 'center'
  },
  tooltip: {
    trigger: 'axis'
  },
  xAxis: {
    type: 'category',
    data: [] as string[]
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      data: [] as number[],
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ]
        }
      },
      itemStyle: {
        color: '#409EFF'
      }
    }
  ]
})

// 模型使用分布图表配置
const modelDistributionOption = ref({
  title: {
    text: '模型使用分布',
    left: 'center'
  },
  tooltip: {
    trigger: 'item'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      type: 'pie',
      radius: '50%',
      data: [] as { name: string; value: number }[],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
})

const fetchStats = async () => {
  loading.value = true
  try {
    const response = await usageApi.getStats({ days: 7 })
    stats.value = response.data.data
    
    // 更新图表数据
    if (stats.value) {
      requestTrendOption.value.xAxis.data = stats.value.requests_by_day.map(d => d.date)
      requestTrendOption.value.series[0].data = stats.value.requests_by_day.map(d => d.count)
      
      modelDistributionOption.value.series[0].data = stats.value.requests_by_model.map(m => ({
        name: m.model,
        value: m.count
      }))
    }
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
  <div class="dashboard">
    <h2>仪表盘</h2>
    
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" v-loading="loading">
          <div class="stat-item">
            <div class="stat-icon" style="background: #409EFF;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总请求数</div>
              <div class="stat-value">{{ stats?.total_requests || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" v-loading="loading">
          <div class="stat-item">
            <div class="stat-icon" style="background: #67C23A;">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总Tokens</div>
              <div class="stat-value">{{ stats?.total_tokens?.toLocaleString() || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" v-loading="loading">
          <div class="stat-item">
            <div class="stat-icon" style="background: #E6A23C;">
              <el-icon><Money /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总费用</div>
              <div class="stat-value">${{ (stats?.total_cost || 0).toFixed(4) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" v-loading="loading">
          <div class="stat-item">
            <div class="stat-icon" style="background: #F56C6C;">
              <el-icon><Key /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">活跃API Keys</div>
              <div class="stat-value">-</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card shadow="hover" v-loading="loading">
          <v-chart class="chart" :option="requestTrendOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover" v-loading="loading">
          <v-chart class="chart" :option="modelDistributionOption" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 0;
}

.dashboard h2 {
  margin-bottom: 20px;
  font-weight: 500;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.stat-icon .el-icon {
  font-size: 28px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.charts-row {
  margin-top: 20px;
}

.chart {
  height: 350px;
}
</style>