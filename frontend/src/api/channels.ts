import request from './request'
import type { AxiosResponse } from 'axios'
import type { 
  ApiResponse, 
  PaginatedResponse, 
  Channel, 
  CreateChannelRequest 
} from '@/types'

export const channelsApi = {
  getChannels(params?: { page?: number; page_size?: number; type?: string }): Promise<AxiosResponse<ApiResponse<PaginatedResponse<Channel>>>> {
    return request.get('/channels', { params })
  },

  createChannel(data: CreateChannelRequest): Promise<AxiosResponse<ApiResponse<Channel>>> {
    return request.post('/channels', data)
  },

  updateChannel(id: number, data: Partial<CreateChannelRequest>): Promise<AxiosResponse<ApiResponse<Channel>>> {
    return request.put(`/channels/${id}`, data)
  },

  deleteChannel(id: number): Promise<AxiosResponse<ApiResponse<void>>> {
    return request.delete(`/channels/${id}`)
  },

  testChannel(id: number): Promise<AxiosResponse<ApiResponse<{ status: string; latency_ms: number; message: string }>>> {
    return request.post(`/channels/${id}/test`)
  }
}