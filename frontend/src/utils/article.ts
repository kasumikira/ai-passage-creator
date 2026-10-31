/**
 * 文章相关工具函数
 */
import { STATUS_TEXT_MAP, STATUS_TAG_COLOR_MAP, STATUS_COLOR_MAP } from '@/constants/article'
import request from '@/request'

/**
 * 获取状态文本
 * @param status 状态值
 */
export const getStatusText = (status: string): string => {
  return STATUS_TEXT_MAP[status] || status
}

/**
 * 获取状态标签颜色（用于 Ant Design Tag）
 * @param status 状态值
 */
export const getStatusTagColor = (status: string): string => {
  return STATUS_TAG_COLOR_MAP[status] || 'default'
}

/**
 * 获取状态颜色（用于自定义样式）
 * @param status 状态值
 */
export const getStatusColor = (status: string): string => {
  return STATUS_COLOR_MAP[status] || '#999'
}

/**
 * 导出文章为 Markdown 文件
 * @param title 文章标题
 * @param subTitle 副标题
 * @param content 正文内容
 * @param fullContent 完整图文内容（可选）
 * @param outline 大纲（可选）
 * @param images 配图列表（可选）
 */
export interface ExportArticleOptions {
  title: string
  subTitle?: string
  content?: string
  fullContent?: string
  outline?: Array<{ section?: number; title?: string }>
  images?: Array<{ description?: string; url?: string }>
}

const readBlobAsDataUrl = (blob: Blob): Promise<string> => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result as string)
  reader.onerror = () => reject(reader.error || new Error('读取图片失败'))
  reader.readAsDataURL(blob)
})

const embedDatabaseImages = async (markdown: string): Promise<string> => {
  const hashes = [...new Set(
    [...markdown.matchAll(/dbimage:\/\/([a-f0-9]{64})/gi)].map((match) => match[1].toLowerCase()),
  )]
  const embeddedImages = await Promise.all(hashes.map(async (hash) => {
    const response = await request.get<Blob>(`/article/images/${hash}`, {
      responseType: 'blob',
    })
    if (!response.data.type.startsWith('image/')) {
      throw new Error('获取文章图片失败')
    }
    return [hash, await readBlobAsDataUrl(response.data)] as const
  }))

  for (const [hash, dataUrl] of embeddedImages) {
    markdown = markdown.replace(new RegExp(`dbimage://${hash}`, 'gi'), dataUrl)
  }
  return markdown
}

export const exportAsMarkdown = async (options: ExportArticleOptions): Promise<void> => {
  const { title, subTitle, content, fullContent, outline, images } = options

  let markdown = `# ${title}\n\n`
  if (subTitle) {
    markdown += `> ${subTitle}\n\n`
  }

  // 优先使用完整图文
  if (fullContent) {
    markdown += fullContent
  } else {
    if (outline && outline.length > 0) {
      markdown += `## 目录\n\n`
      outline.forEach((item) => {
        markdown += `${item.section}. ${item.title}\n`
      })
      markdown += `\n---\n\n`
    }

    markdown += content || ''

    if (images && images.length > 0) {
      markdown += `\n\n## 配图\n\n`
      images.forEach((image) => {
        if (image.url) markdown += `![${image.description || ''}](${image.url})\n\n`
      })
    }
  }

  markdown = await embedDatabaseImages(markdown)
  const blob = new Blob([markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title || '文章'}.md`
  a.click()
  URL.revokeObjectURL(url)
}
