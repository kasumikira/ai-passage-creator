import request from '@/request'

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

export async function importProductProfile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request<BaseResponse<ProductProfile>>('/marketing/products/import', {
    method: 'POST',
    data: formData,
  })
}

export async function deleteProductProfile(id: number) {
  return request<BaseResponse<boolean>>(`/marketing/products/${id}`, { method: 'DELETE' })
}

export async function getMarketingAnalytics() {
  return request<BaseResponse<MarketingAnalytics>>('/marketing/analytics', { method: 'GET' })
}

export async function analyzeMarketingAnalytics(question?: string) {
  return request<BaseResponse<{ analysis: string; toolCalls: number; lastAgent: string }>>(
    '/marketing/analytics/analyze',
    { method: 'POST', data: { question } },
  )
}
