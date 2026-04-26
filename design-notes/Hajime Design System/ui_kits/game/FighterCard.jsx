const fighterCardStyles = {
  card: {
    background: 'var(--paper-card)',
    border: '1px solid var(--paper-dark)',
    borderRadius: 3,
    padding: '16px 18px',
    boxShadow: '2px 3px 0 rgba(60,45,20,0.06)',
    fontFamily: 'var(--font-serif)',
    color: 'var(--ink-black)',
    minWidth: 220,
    cursor: 'pointer',
    transition: 'box-shadow 120ms',
  },
  cardSelected: { boxShadow: '3px 4px 0 rgba(60,45,20,0.14)', borderColor: 'var(--ink-black)' },
  name: { fontSize: 20, margin: '0 0 2px', letterSpacing: '-0.005em' },
  meta: { fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-light)', margin: '0 0 12px' },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
    padding: '3px 0',
    borderBottom: '1px dotted rgba(60,45,20,0.25)',
  },
  val: { fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-soft)' },
  note: { fontStyle: 'italic', fontSize: 12, color: 'var(--ink-light)', marginTop: 10, lineHeight: 1.4 },
};

function FighterCard({ fighter, selected, onClick }) {
  return (
    <div
      style={{ ...fighterCardStyles.card, ...(selected ? fighterCardStyles.cardSelected : {}) }}
      onClick={onClick}
    >
      <h3 style={fighterCardStyles.name}>{fighter.name}</h3>
      <p style={fighterCardStyles.meta}>{fighter.belt} · {fighter.weight} · {fighter.age}</p>
      {fighter.stats.map((s) => (
        <div key={s.k} style={fighterCardStyles.statRow}>
          <span>{s.k}</span>
          <span style={fighterCardStyles.val}>{s.v}</span>
        </div>
      ))}
      {fighter.note && <p style={fighterCardStyles.note}>{fighter.note}</p>}
    </div>
  );
}

window.FighterCard = FighterCard;
