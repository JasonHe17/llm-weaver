// 用户相关类型
export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'user'
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  code: number
  message: string
  data: {
    access_token: string
    token_type: string
    user: User
  }
}

// API Key 相关类型
export interface APIKey {
  id: number
  user_id: number
  name: string
  key_preview: string
  key?: string // 只在创建时返回
  status: 'active' | 'inactive'
  budget_limit: number | null
  budget_used: number
  allowed_models: string[] | null
  rate_limit: number
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateAPIKeyRequest {
  name: string
  budget_limit?: number
  allowed_models?: string[]
  rate_limit?: number
  expires_at?: string
}

// 渠道相关类型
export interface Channel {
  id: number
  user_id: number
  name: string
  type: 'openai' | 'anthropic' | 'azure' | 'gemini' | 'mistral' | 'cohere'
  config: Record<string, any>
  weight: number
  priority: number
  status: 'active' | 'inactive' | 'error'
  is_system: boolean
  last_tested_at: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  models: ModelMapping[]
}

export interface ModelMapping {
  id: number
  channel_id: number
  model_id: string
  mapped_model: string
}

export interface CreateChannelRequest {
  name: string
  type: string
  config: Record<string, any>
  weight: number
  priority: number
  models: { model_id: string; mapped_model: string }[]
}

// 模型相关类型
export interface Model {
  id: string
  name: string
  provider: string
  description: string
  status: 'active' | 'inactive'
  pricing: {
    input_price: number
    output_price: number
  }
  capabilities: string[]
  context_length: number
  created_at: string
  updated_at: string
}

// 用量统计类型
export interface UsageStats {
  total_requests: number
  total_tokens: number
  total_cost: number
  requests_by_model: { model: string; count: number }[]
  cost_by_model: { model: string; cost: number }[]
  requests_by_day: { date: string; count: number }[]
}

export interface RequestLog {
  id: number
  api_key_id: number
  user_id: number
  channel_id: number
  model: string
  status: 'success' | 'error'
  tokens_input: number
  tokens_output: number
  cost: number
  latency_ms: number
  error_message: string | null
  created_at: string
}

// 通用响应类型
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}