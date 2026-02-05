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
const dialogType = ref<'create' | 'edit' | 'view'>('create')
const currentKey = ref<APIKey | null>(null)
const showKeyDialog = ref(false)
const generatedKey = ref('')

const form = ref<CreateAPIKeyRequest>({
  name: '',
  budget_limit: undefined,
  rate_limit: 60,
  allowed_models: []
})

const editForm = ref<{
  id: number
  name: string
  budget_limit?: number
  rate_limit: number
  allowed_models: string[]
  status: 'active' | 'inactive'
}>({
  id: 0,
  name: '',
  budget_limit: undefined,
  rate_limit: 60,
  allowed_models: [],
  status: 'active'
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

const handleEdit = (row: APIKey) => {
  dialogType.value = 'edit'
  editForm.value = {
    id: row.id,
    name: row.name,
    budget_limit: row.budget_limit || undefined,
    rate_limit: row.rate_limit,
    allowed_models: row.allowed_models || [],
    status: row.status
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (dialogType.value === 'create') {
      const response = await apiKeysApi.createApiKey(form.value)
      generatedKey.value = response.data.data.key || ''
      ElMessage.success('API Key创建成功')
      dialogVisible.value = false
      showKeyDialog.value = true
      fetchApiKeys()
    } else if (dialogType.value === 'edit') {
      await apiKeysApi.updateApiKey(editForm.value.id, {
        name: editForm.value.name,
        budget_limit: editForm.value.budget_limit,
        rate_limit: editForm.value.rate_limit,
        allowed_models: editForm.value.allowed_models,
        status: editForm.value.status
      })
      ElMessage.success('API Key更新成功')
      dialogVisible.value = false
      fetchApiKeys()
    }
  } catch (error) {
    console.error('Failed to save API key:', error)
    ElMessage.error('操作失败，请重试')
  }
}

const handleToggleStatus = async (row: APIKey) => {
  try {
    const newStatus = row.status === 'active' ? 'inactive' : 'active'
    await apiKeysApi.updateApiKey(row.id, { status: newStatus })
    ElMessage.success(`API Key已${newStatus === 'active' ? '启用' : '禁用'}`)
    fetchApiKeys()
  } catch (error) {
    console.error('Failed to toggle status:', error)
    ElMessage.error('操作失败')
  }
}

const handleRegenerate = async (row: APIKey) => {
  try {
    await ElMessageBox.confirm(
      '重新生成密钥后，旧密钥将立即失效。确定要继续吗？',
      '确认重新生成',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    const response = await apiKeysApi.regenerateApiKey(row.id)
    generatedKey.value = response.data.data.key || ''
    ElMessage.success('密钥重新生成成功')
    showKeyDialog.value = true
    fetchApiKeys()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to regenerate key:', error)
      ElMessage.error('操作失败')
    }
  }
}

const closeKeyDialog = () => {
  showKeyDialog.value = false
  generatedKey.value = ''
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
         <el-table-column label="使用进度" width="180">
           <template #default="{ row }">
             <div v-if="row.budget_limit" class="budget-progress">
               <el-progress 
                 :percentage="Math.min((row.budget_used / row.budget_limit) * 100, 100)" 
                 :status="(row.budget_used / row.budget_limit) > 0.9 ? 'exception' : ''"
                 :format="(p: number) => `$${row.budget_used.toFixed(2)} / $${row.budget_limit}`"
               />
             </div>
             <span v-else>${{ row.budget_used.toFixed(4) }} / 无限制</span>
           </template>
         </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button 
              :type="row.status === 'active' ? 'warning' : 'success'" 
              link 
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-dropdown trigger="click">
              <el-button type="primary" link>
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleRegenerate(row)">重新生成</el-dropdown-item>
                  <el-dropdown-item divided @click="handleDelete(row)" style="color: #f56c6c;">
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
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

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新建 API Key' : '编辑 API Key'"
      width="500px"
    >
      <template v-if="dialogType === 'create'">
        <el-form :model="form" label-width="100px">
          <el-form-item label="名称" required>
            <el-input v-model="form.name" placeholder="请输入API Key名称" />
          </el-form-item>
          <el-form-item label="预算限制">
            <el-input-number v-model="form.budget_limit" :min="0" :precision="2" placeholder="无限制" />
            <span class="form-hint">美元</span>
          </el-form-item>
          <el-form-item label="速率限制">
            <el-input-number v-model="form.rate_limit" :min="1" :max="10000" />
            <span class="form-hint">请求/分钟</span>
          </el-form-item>
        </el-form>
      </template>
      
      <template v-else-if="dialogType === 'edit'">
        <el-form :model="editForm" label-width="100px">
          <el-form-item label="名称" required>
            <el-input v-model="editForm.name" placeholder="请输入API Key名称" />
          </el-form-item>
          <el-form-item label="预算限制">
            <el-input-number v-model="editForm.budget_limit" :min="0" :precision="2" placeholder="无限制" />
            <span class="form-hint">美元</span>
          </el-form-item>
          <el-form-item label="速率限制">
            <el-input-number v-model="editForm.rate_limit" :min="1" :max="10000" />
            <span class="form-hint">请求/分钟</span>
          </el-form-item>
          <el-form-item label="状态">
            <el-radio-group v-model="editForm.status">
              <el-radio label="active">启用</el-radio>
              <el-radio label="inactive">禁用</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 显示密钥对话框 -->
    <el-dialog
      v-model="showKeyDialog"
      title="API Key 已生成"
      width="550px"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <div class="key-display">
        <el-alert
          title="请立即复制并保存您的 API Key，它只会显示一次！"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 15px;"
        />
        <el-input
          v-model="generatedKey"
          readonly
          type="textarea"
          :rows="3"
          style="margin-bottom: 15px;"
        />
        <div style="text-align: center;">
          <el-button type="primary" size="large" @click="copyKey(generatedKey)">
            <el-icon><DocumentCopy /></el-icon>
            复制到剪贴板
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="closeKeyDialog">我已保存</el-button>
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

.budget-progress {
  width: 100%;
}

.budget-progress :deep(.el-progress-bar__outer) {
  background-color: #e4e7ed;
}

:deep(.el-dropdown) {
  vertical-align: middle;
  margin-left: 8px;
}
</style>