'use client'
import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import ChatArea from '@/components/ChatArea'
import type { IndexedSource } from '@/lib/types'

export default function HomePage() {
  const [sources, setSources] = useState<IndexedSource[]>([])
  return (
    <div className="flex h-full overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      <Sidebar sources={sources} onSourceAdded={s => setSources(prev => [...prev, s])} />
      <ChatArea />
    </div>
  )
}
