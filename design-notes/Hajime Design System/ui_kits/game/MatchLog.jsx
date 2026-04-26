const matchLogStyles = {
  wrap: {
    background: 'var(--ink-black)',
    color: 'var(--gi-cream)',
    fontFamily: 'var(--font-serif)',
    fontSize: 15,
    lineHeight: 1.6,
    padding: '18px 22px',
    minHeight: 260,
    maxHeight: 360,
    overflowY: 'auto',
  },
  line: {
    marginBottom: 6,
    animation: 'hajime-fade 400ms cubic-bezier(0.25,0.1,0.25,1) both',
  },
  time: {
    color: 'var(--amber-bulb)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    marginRight: 10,
    letterSpacing: '0.04em',
  },
  hl: { color: 'var(--amber-bulb)' },
  danger: { color: '#c95a4b' },
};

const matchLogCss = `@keyframes hajime-fade { from { opacity: 0; } to { opacity: 1; } }`;

function MatchLog({ events }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [events.length]);
  return (
    <>
      <style>{matchLogCss}</style>
      <div ref={ref} style={matchLogStyles.wrap}>
        {events.map((e, i) => (
          <div key={i} style={matchLogStyles.line}>
            <span style={matchLogStyles.time}>{e.t}</span>
            {e.parts.map((p, j) => {
              if (p.k === 'hl') return <span key={j} style={matchLogStyles.hl}>{p.s}</span>;
              if (p.k === 'danger') return <span key={j} style={matchLogStyles.danger}>{p.s}</span>;
              return <span key={j}>{p.s}</span>;
            })}
          </div>
        ))}
      </div>
    </>
  );
}

window.MatchLog = MatchLog;
