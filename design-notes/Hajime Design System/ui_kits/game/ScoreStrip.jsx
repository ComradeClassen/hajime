const scoreStripStyles = {
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 24,
    padding: '10px 18px',
    fontFamily: 'var(--font-sans)',
    fontWeight: 300,
    fontSize: 13,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'var(--amber-bulb)',
    background: 'var(--ink-black)',
    borderBottom: '1px solid rgba(212,160,74,0.3)',
    whiteSpace: 'nowrap',
  },
  seg: { whiteSpace: 'nowrap' },
  mid: { color: 'var(--gi-cream)', fontFamily: 'var(--font-serif)', letterSpacing: 0, textTransform: 'none', fontSize: 15, whiteSpace: 'nowrap' },
  score: { fontFamily: 'var(--font-mono)', fontSize: 15, color: 'var(--amber-bulb)', letterSpacing: '0.05em', whiteSpace: 'nowrap' },
};

function ScoreStrip({ round, weight, left, right, leftScore, rightScore, time, state }) {
  return (
    <div style={scoreStripStyles.row}>
      <span style={scoreStripStyles.seg}>{`Round ${round} · ${weight}`}</span>
      <span style={scoreStripStyles.mid}>
        {left} <span style={scoreStripStyles.score}>{leftScore} : {rightScore}</span> {right}
      </span>
      <span style={scoreStripStyles.seg}>{`${time} · ${state}`}</span>
    </div>
  );
}

window.ScoreStrip = ScoreStrip;
