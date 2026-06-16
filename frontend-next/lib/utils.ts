import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function escapeHtml(str: string) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function formatAnswer(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[Source:(.*?)\]/g, '<span class="text-indigo-400 font-medium">[Source:$1]</span>')
    .replace(/\n/g, '<br>')
}

export const SOURCE_ICONS: Record<string, string> = {
  pdf: '📄',
  web: '🌐',
  github: '🐙',
  youtube: '🎥',
}

export function faithBadgeClass(verdict: string) {
  if (verdict === 'FAITHFUL') return 'badge-faithful'
  if (verdict === 'PARTIALLY_FAITHFUL') return 'badge-partial'
  if (verdict === 'NOT_FAITHFUL') return 'badge-unfaithful'
  return 'badge-unknown'
}

export function faithLabel(verdict: string) {
  if (verdict === 'FAITHFUL') return '✓ Faithful'
  if (verdict === 'PARTIALLY_FAITHFUL') return '~ Partial'
  if (verdict === 'NOT_FAITHFUL') return '✗ Hallucination'
  return '? Unchecked'
}

export function confidenceBadgeClass(level: string) {
  if (level === 'high') return 'badge-high'
  if (level === 'medium') return 'badge-medium'
  return 'badge-low'
}
