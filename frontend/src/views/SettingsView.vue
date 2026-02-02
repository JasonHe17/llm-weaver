<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('profile')
</script>

<template>
  <div class="settings">
    <h2>系统设置</h2>
    
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="个人资料" name="profile">
        <el-card>
          <p>个人资料设置功能开发中...</p>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="安全设置" name="security">
        <el-card>
          <p>安全设置功能开发中...</p>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="系统配置" name="system">
        <el-card>
          <p>系统配置功能开发中...</p>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.settings {
  padding: 0;
}

.settings h2 {
  margin-bottom: 20px;
  font-weight: 500;
}
</style>