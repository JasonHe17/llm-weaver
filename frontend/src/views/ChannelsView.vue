<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { channelsApi } from '@/api'
import type { Channel, CreateChannelRequest } from '@/types'

const loading = ref(false)
const channels = ref<Channel[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const dialogType = ref<'create' | 'edit'>('create')
const currentId = ref<number | null>(null)

const channelTypes = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure', label: 'Azure OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
]

// 模型选项
const modelOptions = [
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  { value: 'claude-3-opus', label: 'Claude 3 Opus' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
  { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
  { value: 'gemini-pro', label: 'Gemini Pro' },
  { value: 'gemini-ultra', label: 'Gemini Ultra' },
]

// 测试对话框
const testDialogVisible = ref(false)
const testResult = ref<{
  status: string
  latency_ms: number
  message: string
} | null>(null)

const form = ref<CreateChannelRequest>({
  name: '',
  type: 'openai',
  config: { api_key: '', api_base: '' },
  weight: 100,
  priority: 0,
  models: []
})

const fetchChannels = async () => {
  loading.value = true
  try {
    const response = await channelsApi.getChannels({
      page: currentPage.value,
      page_size: pageSize.value
    })
    channels.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    console.error('Failed to fetch channels:', error)
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogType.value = 'create'
  form.value = {
    name: '',
    type: 'openai',
    config: { api_key: '', api_base: '' },
    weight: 100,
    priority: 0,
    models: []
  }
  currentId.value = null
  dialogVisible.value = true
}

const handleEdit = (row: Channel) => {
  dialogType.value = 'edit'
  form.value = {
    name: row.name,
    type: row.type,
    config: { ...row.config },
    weight: row.weight,
    priority: row.priority,
    models: row.models.map(m => ({ model_id: m.model_id, mapped_model: m.mapped_model }))
  }
  currentId.value = row.id
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (dialogType.value === 'create') {
      await channelsApi.createChannel(form.value)
      ElMessage.success('渠道创建成功')
    } else if (currentId.value) {
      await channelsApi.updateChannel(currentId.value, form.value)
      ElMessage.success('渠道更新成功')
    }
    dialogVisible.value = false
    fetchChannels()
  } catch (error) {
    console.error('Failed to save channel:', error)
  }
}

const handleDelete = async (row: Channel) => {
  try {
    await ElMessageBox.confirm('确定要删除这个渠道吗？', '确认删除', {
      type: 'warning'
    })
    await channelsApi.deleteChannel(row.id)
    ElMessage.success('删除成功')
    fetchChannels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete channel:', error)
    }
  }
}

const handleToggleStatus = async (row: Channel) => {
  try {
    const newStatus = row.status === 'active' ? 'inactive' : 'active'
    await channelsApi.updateChannel(row.id, { status: newStatus })
    ElMessage.success(`渠道已${newStatus === 'active' ? '启用' : '禁用'}`)
    fetchChannels()
  } catch (error) {
    console.error('Failed to toggle status:', error)
    ElMessage.error('操作失败')
  }
}

const handleTest = async (row: Channel) => {
  try {
    const response = await channelsApi.testChannel(row.id)
    testResult.value = response.data.data
    testDialogVisible.value = true
    
    // 刷新列表以更新状态
    fetchChannels()
  } catch (error) {
    console.error('Failed to test channel:', error)
    ElMessage.error('测试失败')
  }
}

// 模型映射管理
const addModelMapping = () => {
  form.value.models.push({
    model_id: '',
    mapped_model: ''
  })
}

const removeModelMapping = (index: number) => {
  form.value.models.splice(index, 1)
}

onMounted(() => {
  fetchChannels()
})
</script>

<template>
  <div class="channels">
    <div class="page-header">
      <h2>渠道管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建渠道
      </el-button>
    </div>

    <el-card>
      <el-table :data="channels" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ channelTypes.find(t => t.value === row.type)?.label || row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'error' ? 'danger' : 'info'">
              {{ row.status === 'active' ? '正常' : row.status === 'error' ? '错误' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="weight" label="权重" width="80" />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button 
              :type="row.status === 'active' ? 'warning' : 'success'" 
              link 
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button type="success" link @click="handleTest(row)">测试</el-button>
            <el-dropdown trigger="click">
              <el-button type="primary" link>
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleDelete(row)" style="color: #f56c6c;">
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
          @change="fetchChannels"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新建渠道' : '编辑渠道'"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="请输入渠道名称" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.type" placeholder="选择类型" style="width: 100%">
            <el-option
              v-for="type in channelTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input v-model="form.config.api_key" placeholder="请输入API Key" show-password />
        </el-form-item>
        <el-form-item label="API Base">
          <el-input v-model="form.config.api_base" placeholder="可选，默认为官方地址" />
        </el-form-item>
        <el-form-item label="权重">
          <el-input-number v-model="form.weight" :min="1" :max="1000" />
        </el-form-item>
         <el-form-item label="优先级">
           <el-input-number v-model="form.priority" :min="0" :max="100" />
           <span class="form-hint">数值越大优先级越高</span>
         </el-form-item>
 
         <el-divider>模型映射</el-divider>
         
         <div v-for="(mapping, index) in form.models" :key="index" class="model-mapping-row">
           <el-row :gutter="10">
             <el-col :span="10">
               <el-select v-model="mapping.model_id" placeholder="选择模型" style="width: 100%">
                 <el-option
                   v-for="model in modelOptions"
                   :key="model.value"
                   :label="model.label"
                   :value="model.value"
                 />
               </el-select>
             </el-col>
             <el-col :span="10">
               <el-input v-model="mapping.mapped_model" placeholder="映射名称（可选）" />
             </el-col>
             <el-col :span="4">
               <el-button type="danger" circle @click="removeModelMapping(index)">
                 <el-icon><Delete /></el-icon>
               </el-button>
             </el-col>
           </el-row>
         </div>
         
         <el-button type="primary" plain @click="addModelMapping" style="margin-top: 10px;">
           <el-icon><Plus /></el-icon>
           添加模型映射
         </el-button>
       </el-form>
 
       <template #footer>
         <el-button @click="dialogVisible = false">取消</el-button>
         <el-button type="primary" @click="handleSubmit">确定</el-button>
       </template>
     </el-dialog>
 
     <!-- 测试结果对话框 -->
     <el-dialog
       v-model="testDialogVisible"
       title="渠道测试结果"
       width="400px"
     >
       <div v-if="testResult" class="test-result">
         <div class="test-status">
           <el-icon :size="48" :color="testResult.status === 'success' ? '#67c23a' : '#f56c6c'">
             <CircleCheck v-if="testResult.status === 'success'" />
             <CircleClose v-else />
           </el-icon>
           <h3>{{ testResult.status === 'success' ? '连接成功' : '连接失败' }}</h3>
         </div>
         <el-descriptions :column="1" border>
           <el-descriptions-item label="延迟">
             {{ testResult.latency_ms }}ms
           </el-descriptions-item>
           <el-descriptions-item label="消息">
             {{ testResult.message }}
           </el-descriptions-item>
         </el-descriptions>
       </div>
       <template #footer>
         <el-button @click="testDialogVisible = false">关闭</el-button>
       </template>
     </el-dialog>
  </div>
</template>

<style scoped>
.channels {
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
  font-size: 12px;
}

.model-mapping-row {
  margin-bottom: 10px;
}

.test-result {
  text-align: center;
}

.test-status {
  margin-bottom: 20px;
}

.test-status h3 {
  margin: 10px 0;
  color: #303133;
}

:deep(.el-dropdown) {
  vertical-align: middle;
  margin-left: 8px;
}
</style>