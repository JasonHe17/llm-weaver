<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiKeysApi } from '@/api'
import type { APIKey, CreateAPIKeyRequest } from '@/types'

const loading = ref(false)
const apiKeys = ref<APIKey[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const dialogType = ref<'create' | 'view'>('create')
const currentKey = ref<APIKey | null>(null)

const form = ref<CreateAPIKeyRequest>({
  name: '',
  budget_limit: undefined,
  rate_limit: 60,
  allowed_models: []
})

const fetchApiKeys = async () => {
  loading.value = true
  try {
    const response = await apiKeysApi.getApiKeys({
      page: currentPage.value,
      page_size: pageSize.value
    })
    apiKeys.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    console.error('Failed to fetch API keys:', error)
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogType.value = 'create'
  form.value = {
    name: '',
    budget_limit: undefined,
    rate_limit: 60,
    allowed_models: []
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    const response = await apiKeysApi.createApiKey(form.value)
    currentKey.value = response.data.data
    ElMessage.success('API Key创建成功')
    dialogVisible.value = false
    fetchApiKeys()
  } catch (error) {
    console.error('Failed to create API key:', error)
  }
}

const handleDelete = async (row: APIKey) => {
  try {
    await ElMessageBox.confirm('确定要删除这个API Key吗？此操作不可恢复。', '确认删除', {
      type: 'warning'
    })
    await apiKeysApi.deleteApiKey(row.id)
    ElMessage.success('删除成功')
    fetchApiKeys()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete API key:', error)
    }
  }
}

const copyKey = (key: string) => {
  navigator.clipboard.writeText(key)
  ElMessage.success('已复制到剪贴板')
}

onMounted(() => {
  fetchApiKeys()
})
</script>

<template>
  <div class="api-keys">
    <div class="page-header">
      <h2>API Keys</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建 API Key
      </el-button>
    </div>

    <el-card>
      <el-table :data="apiKeys" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="key_preview" label="Key" min-width="200">
          <template #default="{ row }">
            <code>{{ row.key_preview }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '活跃' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="budget_limit" label="预算限制" width="120">
          <template #default="{ row }">
            {{ row.budget_limit ? `$${row.budget_limit}` : '无限制' }}
          </template>
        </el-table-column>
        <el-table-column prop="budget_used" label="已使用" width="100">
          <template #default="{ row }">
            ${{ row.budget_used.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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
          @change="fetchApiKeys"
        />
      </div>
    </el-card>

    <!-- 创建/查看对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新建 API Key' : 'API Key 详情'"
      width="500px"
    >
      <template v-if="dialogType === 'create'">
        <el-form :model="form" label-width="100px">
          <el-form-item label="名称" required>
            <el-input v-model="form.name" placeholder="请输入API Key名称" />
          </el-form-item>
          <el-form-item label="预算限制">
            <el-input-number v-model="form.budget_limit" :min="0" :precision="2" placeholder="无限制" />
          </el-form-item>
          <el-form-item label="速率限制">
            <el-input-number v-model="form.rate_limit" :min="1" :max="10000" />
            <span class="form-hint">请求/分钟</span>
          </el-form-item>
        </el-form>
      </template>
      
      <template v-else-if="currentKey?.key">
        <div class="key-display">
          <p class="key-warning">请立即复制并保存您的 API Key，它只会显示一次！</p>
          <el-input v-model="currentKey.key" readonly type="textarea" :rows="3" />
          <el-button type="primary" @click="copyKey(currentKey.key)">复制</el-button>
        </div>
      </template>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.api-keys {
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

.form-hint {
  margin-left: 10px;
  color: #909399;
}

.key-display {
  text-align: center;
}

.key-warning {
  color: #F56C6C;
  margin-bottom: 15px;
}

code {
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
}
</style>