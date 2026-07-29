interface Props {
  message: string
}

export default function LoadingCard({ message }: Props) {
  return (
    <>
      <div className="loading-card">
        <div className="spinner" />
        <h3>Generating Summary</h3>
        <p>{message}</p>
      </div>
      <div className="loading-tip">
        💡 Tip: Concise summaries help you review faster and retain more.
      </div>
    </>
  )
}
