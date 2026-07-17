const STATS = [
  { n: 96, suffix: '%', label: 'verse hit@1' },
  { n: 100, suffix: '%', label: 'safety recall' },
  { n: 0, suffix: '%', label: 'false positives' },
  { n: 98, suffix: '', label: 'tests green' },
]

export default function Stats() {
  return (
    <section id="stats">
      <div className="band">
        {STATS.map((s) => (
          <div className="stat reveal" key={s.label}>
            <div className="n">
              <span data-count={s.n}>0</span>{s.suffix && <sup>{s.suffix}</sup>}
            </div>
            <div className="l">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
