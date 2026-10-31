/**
 * Markdown 工具函数
 */
import { marked } from 'marked'
import { API_BASE_URL } from '@/config/env'

const renderer = new marked.Renderer()
const defaultImageRenderer = renderer.image.bind(renderer)

const escapeHtmlAttribute = (value: string) => value
  .replaceAll('&', '&amp;')
  .replaceAll('"', '&quot;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')

export const resolveArticleImageUrl = (imageReference?: string): string => {
  if (!imageReference) return ''
  const imageHash = imageReference.match(/^dbimage:\/\/([a-f0-9]{64})$/i)
  return imageHash
    ? `${API_BASE_URL}/article/images/${imageHash[1]}`
    : imageReference
}

renderer.image = (token) => {
  const imageReference = token.href.match(/^dbimage:\/\/([a-f0-9]{64})$/i)
  if (!imageReference) return defaultImageRenderer(token)

  const src = resolveArticleImageUrl(token.href)
  const title = token.title ? ` title="${escapeHtmlAttribute(token.title)}"` : ''
  return `<img src="${src}" alt="${escapeHtmlAttribute(token.text)}"${title} crossorigin="use-credentials">`
}

/**
 * 将 Markdown 转换为 HTML
 * @param markdown Markdown 内容
 */
export const markdownToHtml = (markdown?: string): string => {
  return marked(markdown || '', { renderer }) as string
}
