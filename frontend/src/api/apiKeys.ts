import request from './request'
import type { AxiosResponse } from 'axios'
import type { 
  ApiResponse, 
  PaginatedResponse, 
  APIKey, 
  CreateAPIKeyRequest 
} from '@/types'

export const apiKeysApi = {
  getApiKeys(params?: { page?: number; page_size?: number }): Promise<AxiosResponse<ApiResponse<PaginatedResponse<APIKey>>>> {
    return request.get('/api-keys', { params })
  },

  createApiKey(data: CreateAPIKeyRequest): Promise<AxiosResponse<ApiResponse<APIKey>>> {
    return request.post('/api-keys', data)
  },

  deleteApiKey(id: number): Promise<AxiosResponse<ApiResponse<void>>> {
    return request.delete(`/api-keys/${id}`)
  },

  regenerateApiKey(id: number): Promise<AxiosResponse<ApiResponse<APIKey>>> {
    return request.post(`/api-keys/${id}/regenerate`)
  }
}