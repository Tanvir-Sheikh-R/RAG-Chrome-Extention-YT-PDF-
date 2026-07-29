interface Props {
  dark: string
  accent: string
  subtitle: string
}

export default function HeroTitle({ dark, accent, subtitle }: Props) {
  return (
    <>
      <div className="hero-title">
        <span className="dark">{dark}</span>{' '}
        <span className="accent">{accent}</span>
      </div>
      <div className="hero-subtitle">{subtitle}</div>
    </>
  )
}
