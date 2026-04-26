const chairStyles = {
  panel: {
    background: 'rgba(245,237,216,0.06)',
    border: '1px solid rgba(212,160,74,0.35)',
    borderRadius: 3,
    padding: '18px 20px',
    fontFamily: 'var(--font-serif)',
    color: 'var(--gi-cream)',
  },
  title: {
    fontSize: 11,
    letterSpacing: '0.22em',
    textTransform: 'uppercase',
    color: 'var(--amber-bulb)',
    margin: '0 0 12px',
  },
  line: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: 16,
    fontSize: 13,
    padding: '4px 0',
    borderBottom: '1px dotted rgba(212,160,74,0.22)',
    whiteSpace: 'nowrap',
  },
  lineLabel: { whiteSpace: 'nowrap' },
  val: { color: 'var(--amber-bulb)', fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'nowrap' },
  section: { marginTop: 18 },
  note: {
    fontStyle: 'italic',
    color: 'rgba(245,237,216,0.7)',
    fontSize: 13,
    marginTop: 4,
    marginBottom: 14,
    lineHeight: 1.5,
    maxWidth: '52ch',
  },
  chipRow: { marginTop: 6 },
  commit: {
    display: 'inline-block',
    marginTop: 16,
    padding: '9px 16px',
    fontFamily: 'var(--font-serif)',
    fontSize: 12,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    border: '1px solid var(--amber-bulb)',
    background: 'var(--amber-bulb)',
    color: 'var(--ink-black)',
    borderRadius: 2,
    cursor: 'pointer',
    transition: 'all 120ms',
  },
  commitDisabled: {
    border: '1px solid rgba(245,237,216,0.2)',
    background: 'transparent',
    color: 'rgba(245,237,216,0.35)',
    cursor: 'not-allowed',
  },
  counter: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'rgba(245,237,216,0.5)',
    marginLeft: 12,
    letterSpacing: '0.05em',
  },
};

const INSTRUCTIONS = [
  { id: 'stance', label: 'Switch stance' },
  { id: 'grip', label: 'Break his grip' },
  { id: 'patient', label: 'Stay patient' },
  { id: 'ground', label: 'Go to the ground' },
  { id: 'tighten', label: 'Tighten up' },
  { id: 'posture', label: 'Head up · posture' },
];

function CoachChair({ fighter, stats, note, onResume }) {
  const [picked, setPicked] = React.useState([]);
  const toggle = (id) => {
    setPicked((p) => {
      if (p.includes(id)) return p.filter((x) => x !== id);
      if (p.length >= 2) return p;
      return [...p, id];
    });
  };
  return (
    <div style={chairStyles.panel}>
      <p style={chairStyles.title}>— Coach's chair · {fighter} —</p>
      {stats.map((s) => (
        <div key={s.label} style={chairStyles.line}>
          <span style={chairStyles.lineLabel}>{s.label}</span>
          <span style={chairStyles.val}>{s.val}</span>
        </div>
      ))}
      <div style={chairStyles.section}>
        <p style={chairStyles.title}>What you saw</p>
        <p style={chairStyles.note}>{note}</p>
        <p style={chairStyles.title}>Two instructions<span style={chairStyles.counter}>{picked.length} / 2</span></p>
        <div style={chairStyles.chipRow}>
          {INSTRUCTIONS.map((i) => (
            <InstructionChip
              key={i.id}
              label={i.label}
              active={picked.includes(i.id)}
              disabled={!picked.includes(i.id) && picked.length >= 2}
              onClick={() => toggle(i.id)}
            />
          ))}
        </div>
        <button
          style={{ ...chairStyles.commit, ...(picked.length === 0 ? chairStyles.commitDisabled : {}) }}
          disabled={picked.length === 0}
          onClick={() => onResume(picked)}
        >
          Resume the match
        </button>
      </div>
    </div>
  );
}

window.CoachChair = CoachChair;
