const chipStyles = {
  base: {
    display: 'inline-block',
    padding: '7px 13px',
    fontFamily: 'var(--font-serif)',
    fontSize: 12,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    borderRadius: 2,
    cursor: 'pointer',
    userSelect: 'none',
    marginRight: 6,
    marginBottom: 6,
    transition: 'all 120ms cubic-bezier(0.25,0.1,0.25,1)',
    background: 'transparent',
  },
  inactive: { border: '1px solid var(--amber-bulb)', color: 'var(--amber-bulb)' },
  inactiveHover: { border: '1px solid var(--amber-glow)', color: 'var(--amber-glow)' },
  active: { border: '1px solid var(--oxblood)', color: 'var(--gi-cream)', background: 'var(--oxblood)' },
  disabled: { border: '1px solid rgba(245,237,216,0.18)', color: 'rgba(245,237,216,0.35)', cursor: 'not-allowed' },
};

function InstructionChip({ label, active, disabled, onClick }) {
  const [hover, setHover] = React.useState(false);
  let look = chipStyles.inactive;
  if (disabled) look = chipStyles.disabled;
  else if (active) look = chipStyles.active;
  else if (hover) look = chipStyles.inactiveHover;
  return (
    <span
      style={{ ...chipStyles.base, ...look }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={disabled ? undefined : onClick}
    >
      {label}
    </span>
  );
}

window.InstructionChip = InstructionChip;
