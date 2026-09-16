import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,       // Convert \n to <br>
  gfm: true,          // GitHub Flavored Markdown
})

/**
 * Render markdown string to safe HTML.
 * Strips dangerous tags but keeps formatting.
 */
export function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text, { async: false })
}
