import { useState, useRef, useCallback } from 'react'

interface Props {
  mode: 'youtube' | 'document'
  onModeChange: (mode: 'youtube' | 'document') => void
  onSubmitYoutube: (url: string) => void
  onSubmitDocument: (file: File) => void
}

export default function InputSection({ mode, onModeChange, onSubmitYoutube, onSubmitDocument }: Props) {
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((f: File) => {
    if (!f.name.toLowerCase().endsWith('.txt') && !f.name.toLowerCase().endsWith('.pdf')) return
    setFile(f)
    onSubmitDocument(f)
  }, [onSubmitDocument])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }, [handleFile])

  return (
    <>
      <div className="toggle-row">
        <button className={`toggle-btn${mode === 'document' ? ' active' : ''}`} onClick={() => onModeChange('document')}>
          📄 Document
        </button>
        <button className={`toggle-btn${mode === 'youtube' ? ' active' : ''}`} onClick={() => onModeChange('youtube')}>
          ▶ YouTube
        </button>
      </div>

      {mode === 'youtube' ? (
        <div className="input-row">
          <input
            type="text"
            placeholder="Paste a YouTube URL here..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button className="btn" disabled={!url} onClick={() => onSubmitYoutube(url)}>
            Summarize →
          </button>
        </div>
      ) : (
        <div
          className={`upload-area${dragging ? ' drag-over' : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.pdf"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFile(f)
            }}
          />
          {file ? (
            <div>
              <div className="upload-icon">📄</div>
              <div className="upload-text">{file.name}</div>
            </div>
          ) : (
            <div className="upload-label">
              <div className="upload-icon">📂</div>
              <div className="upload-text">Click or drag a .txt or .pdf file here</div>
            </div>
          )}
        </div>
      )}
    </>
  )
}
