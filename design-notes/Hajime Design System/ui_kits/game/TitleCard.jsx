const titleStyles = {
  stage: {
    position: 'relative',
    background: 'var(--bg)',
    color: 'var(--fg)',
    fontFamily: 'var(--font-serif)',
    backgroundImage:
      'radial-gradient(ellipse at 20% 30%, rgba(212,160,74,0.14), transparent 55%), radial-gradient(ellipse at 85% 90%, rgba(123,36,24,0.12), transparent 55%)',
    padding: '80px 64px',
    minHeight: 560,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  kicker: {
    fontSize: 11,
    letterSpacing: '0.22em',
    textTransform: 'uppercase',
    color: 'rgba(245,237,216,0.55)',
    margin: 0,
  },
  mark: {
    fontFamily: 'var(--font-serif)',
    fontSize: 112,
    lineHeight: 1,
    letterSpacing: '-0.01em',
    margin: '14px 0 6px',
  },
  sub: {
    fontStyle: 'italic',
    color: 'var(--oxblood)',
    letterSpacing: '0.1em',
    fontSize: 17,
    margin: 0,
  },
  tagline: {
    maxWidth: '46ch',
    marginTop: 44,
    fontSize: 17,
    lineHeight: 1.6,
    color: 'rgba(245,237,216,0.72)',
    fontStyle: 'italic',
  },
  cta: {
    marginTop: 36,
    display: 'inline-block',
    border: '1px solid var(--amber-bulb)',
    color: 'var(--amber-bulb)',
    background: 'transparent',
    padding: '10px 18px',
    fontFamily: 'var(--font-serif)',
    fontSize: 13,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    cursor: 'pointer',
    borderRadius: 2,
    alignSelf: 'flex-start',
    transition: 'color 120ms, border-color 120ms',
  },
  footer: {
    position: 'absolute',
    bottom: 24,
    left: 64,
    right: 64,
    fontSize: 11,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: 'rgba(245,237,216,0.35)',
    display: 'flex',
    justifyContent: 'space-between',
  },
};

function TitleCard({ onEnter }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div style={titleStyles.stage} data-screen-label="01 Title">
      <p style={titleStyles.kicker}>A judo coaching simulator</p>
      <div style={titleStyles.mark}>Hajime</div>
      <div style={titleStyles.sub}>— 始め —</div>
      <p style={titleStyles.tagline}>
        You are in the chair beside the mat. When the referee calls <em>matte</em>, you have two words.
      </p>
      <button
        style={{
          ...titleStyles.cta,
          color: hover ? 'var(--amber-glow)' : 'var(--amber-bulb)',
          borderColor: hover ? 'var(--amber-glow)' : 'var(--amber-bulb)',
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={onEnter}
      >
        Enter the dojo
      </button>
      <div style={titleStyles.footer}>
        <span>Cranford · New Jersey</span>
        <span>v0.1 · prototype</span>
      </div>
    </div>
  );
}

window.TitleCard = TitleCard;
