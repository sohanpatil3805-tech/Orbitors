// Shared inline styles for the views (kept out of ui.jsx so React fast refresh works)

export const PAGE_STYLE = { padding: '84px 28px 30px', height: '100vh', overflowY: 'auto', boxSizing: 'border-box' };

export const buttonStyle = (variant = 'default', active = false) => {
  const v = {
    default: { background: active ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.06)', border: `1px solid ${active ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.15)'}`, color: '#f8fafc' },
    danger: { background: 'rgba(220, 38, 38, 0.2)', border: '1px solid #dc2626', color: '#f87171' },
    ok: { background: 'rgba(16, 185, 129, 0.18)', border: '1px solid #10b981', color: '#34d399' },
    primary: { background: 'rgba(56, 189, 248, 0.18)', border: '1px solid #38bdf8', color: '#7dd3fc' },
  }[variant];
  return { ...v, padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' };
};

export const inputStyle = {
  background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.12)', color: '#f8fafc', borderRadius: 6,
  padding: '5px 8px', fontSize: 12, outline: 'none',
};
