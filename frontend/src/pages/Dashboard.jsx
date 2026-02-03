import { useState } from 'react'

function Logo({ size = 22 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <rect x="1" y="9" width="4" height="14" rx="2" fill="#f97316" opacity="0.6" />
        <rect x="7" y="5" width="4" height="22" rx="2" fill="#f97316" opacity="0.75" />
        <rect x="13" y="11" width="4" height="10" rx="2" fill="#f97316" opacity="0.55" />
        <rect x="19" y="3" width="4" height="26" rx="2" fill="#f97316" />
        <rect x="25" y="7" width="4" height="18" rx="2" fill="#f97316" opacity="0.7" />
      </svg>
      <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '18px', letterSpacing: '3px', color: '#fff' }}>CLIPVOX</span>
    </div>
  )
}

export default function Dashboard({ onBack }) {
  const [credits] = useState(500)

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: '#0a0a0e', color: '#fff', minHeight: '100vh' }}>
      <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet" />
      <style>{`* { margin: 0; padding: 0; box-sizing: border-box; }`}</style>

      {/* Navbar Dashboard */}
      <nav style={{
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        padding: '16px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(8,8,12,0.95)', backdropFilter: 'blur(10px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div onClick={onBack} style={{ cursor: 'pointer', opacity: 0.6, fontSize: '13px', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}
            onMouseEnter={e => e.currentTarget.style.opacity = '1'}
            onMouseLeave={e => e.currentTarget.style.opacity = '0.6'}
          >← Voltar</div>
          <Logo />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.2)',
            borderRadius: '8px', padding: '6px 14px'
          }}>
            <span style={{ color: '#f97316', fontSize: '14px' }}>💎</span>
            <span style={{ color: '#f97316', fontWeight: 600, fontSize: '14px' }}>{credits} créditos</span>
          </div>
          <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, #f97316, #ea580c)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>U</div>
        </div>
      </nav>

      {/* Content — placeholder para próximo passo */}
      <div style={{ maxWidth: '900px', margin: '60px auto', padding: '0 32px', textAlign: 'center' }}>
        <div style={{
          border: '2px dashed rgba(255,255,255,0.1)',
          borderRadius: '24px', padding: '80px 40px',
          background: 'rgba(16,16,24,0.5)'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎵</div>
          <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '28px', letterSpacing: '2px', color: '#fff', marginBottom: '10px' }}>
            DASHBOARD EM DESENVOLVIMENTO
          </h2>
          <p style={{ color: '#6b7280', fontSize: '15px', maxWidth: '420px', margin: '0 auto' }}>
            Em breve você vai poder fazer upload da sua música e acompanhar a geração do videoclipe aqui.
          </p>
        </div>
      </div>
    </div>
  )
}
