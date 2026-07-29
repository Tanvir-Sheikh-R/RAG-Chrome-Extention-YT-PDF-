import { useState, useRef } from 'react'
import HeroTitle from './components/HeroTitle'
import InputSection from './components/InputSection'
import LoadingCard from './components/LoadingCard'
import ResultsView from './components/ResultsView'
import ChatPanel from './components/ChatPanel'
import type { Source, ChatMessage } from './api'
import { ingestYoutube, ingestDocument, sendChat } from './api'

type Stage = 'input' | 'loading' | 'results'

export default function App() {
  const [stage, setStage] = useState<Stage>('input')
  const [inputMode, setInputMode] = useState<'youtube' | 'document'>('youtube')
  const [source, setSource] = useState<Source | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const loadingMsg = useRef('')

  async function handleSubmitYoutube(url: string) {
    loadingMsg.current = 'Fetching transcript and generating summary...'
    setStage('loading')
    try {
      const result = await ingestYoutube(url)
      setSource(result)
      setChatHistory([])
      setStage('results')
    } catch {
      setStage('input')
    }
  }

  async function handleSubmitDocument(file: File) {
    loadingMsg.current = 'Reading document and generating summary...'
    setStage('loading')
    try {
      const result = await ingestDocument(file)
      setSource(result)
      setChatHistory([])
      setStage('results')
    } catch {
      setStage('input')
    }
  }

  function handleNew() {
    setStage('input')
    setSource(null)
    setChatHistory([])
  }

  async function handleChat(question: string) {
    if (!source) return
    const newHistory = [...chatHistory, { role: 'user' as const, content: question }]
    setChatHistory(newHistory)
    const answer = await sendChat(source.source_id, question, chatHistory)
    setChatHistory([...newHistory, { role: 'assistant', content: answer }])
  }

  return (
    <div className="app">
      {stage === 'input' && (
        <>
          <HeroTitle dark="AI Content" accent="Summarizer" subtitle="Summarize any YouTube video or document instantly with AI." />
          <InputSection mode={inputMode} onModeChange={setInputMode} onSubmitYoutube={handleSubmitYoutube} onSubmitDocument={handleSubmitDocument} />
        </>
      )}

      {stage === 'loading' && <LoadingCard message={loadingMsg.current} />}

      {stage === 'results' && source && (
        <>
          <div className="back-row">
            <button className="btn btn-outline" onClick={handleNew}>{'← New summary'}</button>
          </div>
          <div className="results-layout">
            <ResultsView source={source} />
            <ChatPanel chatHistory={chatHistory} onSend={handleChat} />
          </div>
        </>
      )}
    </div>
  )
}
