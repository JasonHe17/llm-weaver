import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/views/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '仪表盘', icon: 'DataLine' }
      },
      {
        path: 'api-keys',
        name: 'ApiKeys',
        component: () => import('@/views/ApiKeysView.vue'),
        meta: { title: 'API Keys', icon: 'Key' }
      },
      {
        path: 'channels',
        name: 'Channels',
        component: () => import('@/views/ChannelsView.vue'),
        meta: { title: '渠道管理', icon: 'Connection' }
      },
      {
        path: 'models',
        name: 'Models',
        component: () => import('@/views/ModelsView.vue'),
        meta: { title: '模型管理', icon: 'Cpu' }
      },
      {
        path: 'usage',
        name: 'Usage',
        component: () => import('@/views/UsageView.vue'),
        meta: { title: '用量统计', icon: 'TrendCharts' }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/LogsView.vue'),
        meta: { title: '请求日志', icon: 'Document' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '系统设置', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.public) {
    // 公开页面直接放行
    next()
  } else if (!userStore.isAuthenticated) {
    // 未登录，重定向到登录页
    next('/login')
  } else {
    // 已登录，正常访问
    next()
  }
})

export default router