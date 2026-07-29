const API_BASE = '/api'

export interface Source {
  source_id: string
  whole_content: string
  summary: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function ingestYoutube(url: string): Promise<Source> {
  const form = new FormData()
  form.append('url', url)
  const res = await fetch(`${API_BASE}/ingest/youtube`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function ingestDocument(file: File): Promise<Source> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/ingest/document`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function sendChat(
  sourceId: string,
  question: string,
  chatHistory: ChatMessage[],
): Promise<string> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_id: sourceId, question, chat_history: chatHistory }),
  })
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.answer
}
