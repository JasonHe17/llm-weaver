import request from './request'
import type { AxiosResponse } from 'axios'
import type { ApiResponse, PaginatedResponse, Model } from '@/types'

export const modelsApi = {
  getModels(params?: { page?: number; page_size?: number }): Promise<AxiosResponse<ApiResponse<PaginatedResponse<Model>>>> {
    return request.get('/models', { params })
  },

  getAllActiveModels(): Promise<AxiosResponse<ApiResponse<Model[]>>> {
    return request.get('/models/all')
  }
}