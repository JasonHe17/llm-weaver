import request from './request'
import type { AxiosResponse } from 'axios'
import type { LoginRequest, LoginResponse, ApiResponse, User } from '@/types'

export const authApi = {
  login(data: LoginRequest): Promise<AxiosResponse<LoginResponse>> {
    return request.post('/auth/login', data)
  },

  getCurrentUser(): Promise<AxiosResponse<ApiResponse<User>>> {
    return request.get('/auth/me')
  },

  changePassword(oldPassword: string, newPassword: string): Promise<AxiosResponse<ApiResponse<void>>> {
    return request.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    })
  }
}