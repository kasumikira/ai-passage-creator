import request from '@/request'

export interface ProvenanceEvent {
  id: number
  eventType: 'MATERIAL' | 'TOOL'
  snapshotId: number | null
  toolName: string | null
  arguments: Record<string, unknown> | null
  status: string
  resultSummary: string
  errorMessage: string | null
  sourceRefs: string[] | null
  durationMs: number | null
  createTime: string
  sourceType: string | null
  sourceRef: string | null
  versionTag: string | null
  contentHash: string | null
  summary: string | null
}

export interface MaterialSnapshot {
  id: number
  sourceType: string
  sourceRef: string
  versionTag: string
  contentHash: string
  contentText: string
  summary: string
  createTime: string
}

export async function getArticleTrace(taskId: string) {
  return request<{ code: number; data: ProvenanceEvent[]; message: string }>(
    `/article/${encodeURIComponent(taskId)}/trace`,
    { method: 'GET' },
  )
}

export async function getArticleMaterial(taskId: string, snapshotId: number) {
  return request<{ code: number; data: MaterialSnapshot; message: string }>(
    `/article/${encodeURIComponent(taskId)}/materials/${snapshotId}`,
    { method: 'GET' },
  )
}
