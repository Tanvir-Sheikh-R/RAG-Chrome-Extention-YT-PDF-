import { useState } from 'react'
import type { Source } from '../api'

interface Props {
  source: Source
}

export default function ResultsView({ source }: Props) {
  const [view, setView] = useState<'original' | 'summary'>('summary')

  return (
    <div>
      <div className="content-tabs">
        <button className={`toggle-btn${view === 'original' ? ' active' : ''}`} onClick={() => setView('original')}>
          Original Content
        </button>
        <button className={`toggle-btn${view === 'summary' ? ' active' : ''}`} onClick={() => setView('summary')}>
          Summary
        </button>
      </div>
      <div className="content-card">
        {view === 'original'
          ? source.whole_content.split('\n').map((line, i) => <p key={i}>{line}<br /></p>)
          : source.summary.split('\n').map((line, i) => <p key={i}>{line}<br /></p>)
        }
      </div>
    </div>
  )
}
