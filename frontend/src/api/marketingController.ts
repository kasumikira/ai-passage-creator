import request from '@/request'
import { API_BASE_URL } from '@/config/env'

export interface MarketingPlatform {
  id: number
  platformKey: string
  name: string
  audienceDescription: string
  contentRules: string
  preferredFormats: string
}

export interface ProductProfile {
  id: number
  name: string
  sourceFilename: string
  createTime: string
  profile: {
    name: string
    category: string
    description: string
    coreFeatures: string[]
    targetAudience: string
    sellingPoints: string[]
    differentiators: string[]
    useCases: string[]
    brandTone: string
    claimsToAvoid: string[]
    faq: Array<{ question: string; answer: string }>
    keywords: string[]
  }
}

export interface ProductImportProgress {
  stage: string
  message: string
}

interface ProductImportEvent {
  type: 'progress' | 'complete' | 'error'
  stage?: string
  message?: string
  product?: ProductProfile
}

export interface MarketingAnalytics {
  period: string
  summary: {
    impressions: number
    engagements: number
    clicks: number
    conversions: number
    engagementRate: number
    clickThroughRate: number
    conversionRate: number
  }
  trend: Array<{ date: string; impressions: number; engagements: number; conversions: number }>
  platforms: Array<{
    platform: string
    impressions: number
    engagements: number
    clicks: number
    conversions: number
    engagementRate: number
    conversionRate: number
  }>
  topContent: Array<{
    title: string
    platform: string
    impressions: number
    engagements: number
    conversions: number
  }>
}

export interface MarketingToolCall {
  name: string
  arguments: Record<string, unknown>
}

interface BaseResponse<T> {
  code: number
  data: T
  message: string
}

export async function getMarketingPlatforms() {
  return request<BaseResponse<MarketingPlatform[]>>('/marketing/platforms', { method: 'GET' })
}

export async function updateMarketingPlatform(
  id: number,
  data: Omit<MarketingPlatform, 'id' | 'platformKey'>,
) {
  return request<BaseResponse<MarketingPlatform>>(`/marketing/platforms/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    data,
  })
}

export async function getProductProfiles() {
  return request<BaseResponse<ProductProfile[]>>('/marketing/products', { method: 'GET' })
}

export async function importProductProfile(
  file: File,
  onProgress: (progress: ProductImportProgress) => void,
): Promise<ProductProfile> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, '')}/marketing/products/import`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
    headers: { Accept: 'text/event-stream' },
  })

  if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
    const payload = await response.json().catch(() => undefined) as BaseResponse<null> | undefined
    throw new Error(payload?.message || '产品档案导入请求失败')
  }
  if (!response.body) throw new Error('浏览器不支持读取导入进度流')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let product: ProductProfile | undefined

  const consumeFrame = (frame: string) => {
    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
    if (!data) return

    const event = JSON.parse(data) as ProductImportEvent
    if (event.type === 'progress') {
      onProgress({ stage: event.stage || '', message: event.message || '' })
    } else if (event.type === 'complete' && event.product) {
      product = event.product
    } else if (event.type === 'error') {
      throw new Error(event.message || '产品档案整理失败')
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() || ''
      frames.forEach(consumeFrame)
      if (done) {
        if (buffer.trim()) consumeFrame(buffer)
        break
      }
    }
  } finally {
    reader.releaseLock()
  }

  if (!product) throw new Error('导入进度连接已结束，但服务器没有返回产品档案')
  return product
}

export async function deleteProductProfile(id: number) {
  return request<BaseResponse<boolean>>(`/marketing/products/${id}`, { method: 'DELETE' })
}

export async function getMarketingAnalytics() {
  return request<BaseResponse<MarketingAnalytics>>('/marketing/analytics', { method: 'GET' })
}

export async function analyzeMarketingAnalytics(question?: string) {
  return request<BaseResponse<{
    analysis: string
    toolCalls: number
    toolCallDetails: MarketingToolCall[]
    lastAgent: string
  }>>(
    '/marketing/analytics/analyze',
    { method: 'POST', data: { question } },
  )
}
