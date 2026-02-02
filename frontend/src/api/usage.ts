import request from './request'
import type { AxiosResponse } from 'axios'
import type { ApiResponse, UsageStats, RequestLog, PaginatedResponse } from '@/types'

export const usageApi = {
  // 按日期范围获取统计
  getSummary(params?: { start_date?: string; end_date?: string }): Promise<AxiosResponse<ApiResponse<any>>> {
    return request.get('/usage/summary', { params })
  },

  // 按天数获取统计（简化版）
  getStats(params?: { days?: number }): Promise<AxiosResponse<ApiResponse<UsageStats>>> {
    return request.get('/usage/stats', { params })
  },

  getLogs(params?: { page?: number; page_size?: number; model?: string; status?: string }): Promise<AxiosResponse<ApiResponse<PaginatedResponse<RequestLog>>>> {
    return request.get('/usage/logs', { params })
  }
}