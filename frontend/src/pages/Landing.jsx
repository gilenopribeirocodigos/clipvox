import { useState, useEffect } from 'react'

// ─── DADOS ESTÁTICOS ─────────────────────────────────────────
const WAVEFORM_BARS = Array.from({ length: 100 }, (_, i) => ({
  height: 18 + ((i * 41 + 7) % 65),
  duration: 1.3 + ((i * 19 + 3) % 15) / 10,
  delay: ((i * 0.09) % 2.8).toFixed(2)
}))

const STEPS = [
  { step: '01', title: 'Plan', desc: 'A IA cria um plano completo de direção para o videoclipe', icon: '🎯', color: '#f97316' },
  { step: '02', title: 'Input Analyzing', desc: 'Detecção automática de BPM, tonalidade e perfil de energia', icon: '🔍', color: '#fb923c' },
  { step: '03', title: 'Creative Concept', desc: "Director's Vision: estilo visual, paleta de cores e atmosfera", icon: '🎨', color: '#fdba74' },
  { step: '04', title: 'Scenes', desc: 'Geração de 20+ cenas sincronizadas com a música', icon: '🎬', color: '#06b6d4' },
  { step: '05', title: 'Video Segments', desc: 'Criação dos segmentos de vídeo por IA generativa', icon: '🎥', color: '#22d3ee' },
  { step: '06', title: 'Merge Final', desc: 'Montagem e fusão automática do videoclipe completo', icon: '✨', color: '#67e8f9' }
]

const FEATURES = [
  { title: 'Análise Musical Profunda', desc: 'Detecção automática de BPM, tonalidade, energia e seções da música para sincronização perfeita com cada cena.', icon: '📊' },
  { title: 'Direção Artística por IA', desc: 'Conceito criativo completo gerado automaticamente: estilo visual, paleta de cores, texturas e atmosfera cinematográfica.', icon: '🎭' },
  { title: 'Múltiplos Estilos Visuais', desc: 'Fotorrealista, cinematográfico, animado, retro e muito mais. Escolha o estilo que combina com sua música.', icon: '🖼️' },
  { title: 'Sincronização Automática', desc: 'Cada cena sincroniza perfeitamente com os beats e mudanças de energia da sua música em tempo real.', icon: '⚡' },
  { title: 'Exportação até 4K', desc: 'Vídeos em alta resolução prontos para upload no YouTube, Instagram Reels e TikTok sem perda de qualidade.', icon: '📹' },
  { title: 'Templates Pré-feitos', desc: 'Centenas de templates pensados para forró, sertanejo, funk, pagode e os principais gêneros brasileiros.', icon: '📦' }
]

const PLANS = [
  {
    name: 'Starter', price: 'Grátis', sub: 'Para começar', videos: '3 videoclips/mês',
    features: ['Resolução 720p', 'Com watermark', '2 estilos visuais', 'Suporte básico'],
    highlight: false, cta: 'Começar Grátis'
  },
  {
    name: 'Pro', price: 'R$ 49', sub: 'Mais popular', videos: '20 videoclips/mês',
    features: ['Resolução 1080p', 'Sem watermark', '10 estilos visuais', 'Suporte prioritário', 'Templates exclusivos', 'Edição de cenas'],
    highlight: true, cta: 'Assinar Agora'
  },
  {
    name: 'Enterprise', price: 'R$ 149', sub: 'Para agências', videos: '100 videoclips/mês',
    features: ['Resolução 4K', 'Sem watermark', 'Todos os estilos', 'Suporte 24/7', 'Acesso à API', 'Branding customizado', 'Relatórios de uso'],
    highlight: false, cta: 'Fale Conosco'
  }
]

// ─── COMPONENTES ──────────────────────────────────────────────

function Logo({ size = 28 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <rect x="1" y="9" width="4" height="14" rx="2" fill="#f97316" opacity="0.6" />
        <rect x="7" y="5" width="4" height="22" rx="2" fill="#f97316" opacity="0.75" />
        <rect x="13" y="11" width="4" height="10" rx="2" fill="#f97316" opacity="0.55" />
        <rect x="19" y="3" width="4" height="26" rx="2" fill="#f97316" />
        <rect x="25" y="7" width="4" height="18" rx="2" fill="#f97316" opacity="0.7" />
      </svg>
      <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: size === 28 ? '22px' : '16px', letterSpacing: '3px', color: '#fff' }}>
        CLIPVOX
      </span>
    </div>
  )
}

function Navbar({ scrolled, onGetStarted }) {
  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      padding: scrolled ? '14px 40px' : '22px 40px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      background: scrolled ? 'rgba(8,8,12,0.92)' : 'rgba(10,10,14,0.7)',
      backdropFilter: 'blur(14px)',
      borderBottom: scrolled ? '1px solid rgba(255,255,255,0.07)' : '1px solid transparent',
      transition: 'all 0.4s ease'
    }}>
      <Logo />
      <div style={{ display: 'flex', gap: '30px', alignItems: 'center' }}>
        {['Features', 'Como Funciona', 'Preços'].map(item => (
          <a key={item} style={{ color: '#9ca3af', textDecoration: 'none', fontSize: '14px', fontWeight: 500, cursor: 'pointer', transition: 'color 0.3s' }}
            onMouseEnter={e => e.target.style.color = '#f97316'}
            onMouseLeave={e => e.target.style.color = '#9ca3af'}
          >{item}</a>
        ))}
        <button onClick={onGetStarted} style={{
          background: 'linear-gradient(135deg, #f97316, #ea580c)',
          color: '#fff', border: 'none', borderRadius: '8px',
          padding: '10px 22px', fontSize: '14px', fontWeight: 600,
          cursor: 'pointer', transition: 'transform 0.2s, box-shadow 0.2s'
        }}
          onMouseEnter={e => { e.target.style.transform = 'scale(1.05)'; e.target.style.boxShadow = '0 4px 20px rgba(249,115,22,0.4)'; }}
          onMouseLeave={e => { e.target.style.transform = 'scale(1)'; e.target.style.boxShadow = 'none'; }}
        >Começar Grátis</button>
      </div>
    </nav>
  )
}

function WaveformBg() {
  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0,
      height: '55%', display: 'flex', alignItems: 'flex-end',
      justifyContent: 'center', gap: '2px', opacity: 0.1, pointerEvents: 'none'
    }}>
      {WAVEFORM_BARS.map((bar, i) => (
        <div key={i} style={{
          width: '3px',
          height: `${bar.height}px`,
          background: 'linear-gradient(to top, #f97316, #fb923c, #fdba74)',
          borderRadius: '2px',
          transformOrigin: 'bottom',
          animation: `barPulse ${bar.duration}s ease-in-out ${bar.delay}s infinite`
        }} />
      ))}
    </div>
  )
}

function Hero({ onGetStarted }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => { setTimeout(() => setVisible(true), 100) }, [])

  return (
    <section style={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', paddingTop: '80px' }}>
      <WaveformBg />
      <div style={{ position: 'absolute', top: '15%', left: '5%', width: '450px', height: '450px', background: 'radial-gradient(circle, rgba(249,115,22,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '5%', right: '10%', width: '350px', height: '350px', background: 'radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ position: 'relative', zIndex: 2, textAlign: 'center', maxWidth: '820px', padding: '0 24px' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.25)',
          borderRadius: '20px', padding: '6px 18px', marginBottom: '32px',
          opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.6s ease'
        }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f97316', animation: 'glowDot 2s ease-in-out infinite' }} />
          <span style={{ fontSize: '13px', color: '#f97316', fontWeight: 500 }}>Gerador de Videoclipes com IA</span>
        </div>

        <h1 style={{
          fontFamily: "'Bebas Neue', sans-serif",
          fontSize: 'clamp(56px, 10vw, 100px)', lineHeight: 1.05, letterSpacing: '3px',
          color: '#fff', marginBottom: '20px',
          opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(30px)',
          transition: 'all 0.7s ease 0.1s'
        }}>
          CRIE VIDEOCLIPS<br />
          <span style={{ background: 'linear-gradient(135deg, #f97316 0%, #fb923c 40%, #fdba74 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            COM INTELIGÊNCIA ARTIFICIAL
          </span>
        </h1>

        <p style={{
          fontSize: '18px', color: '#7a8494', lineHeight: 1.7, maxWidth: '580px', margin: '0 auto 40px', fontWeight: 300,
          opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.7s ease 0.2s'
        }}>
          Faça upload da sua música e a IA gera um videoclipe profissional completo em minutos. Sem edição manual. Sem complexidade.
        </p>

        <div style={{
          display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap',
          opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.7s ease 0.3s'
        }}>
          <button onClick={onGetStarted} style={{
            background: 'linear-gradient(135deg, #f97316, #ea580c)',
            color: '#fff', border: 'none', borderRadius: '12px',
            padding: '16px 38px', fontSize: '16px', fontWeight: 600,
            cursor: 'pointer', transition: 'all 0.3s',
            boxShadow: '0 4px 24px rgba(249,115,22,0.35)'
          }}
            onMouseEnter={e => { e.target.style.transform = 'translateY(-2px)'; e.target.style.boxShadow = '0 8px 32px rgba(249,115,22,0.5)'; }}
            onMouseLeave={e => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 4px 24px rgba(249,115,22,0.35)'; }}
          >🎵 Gerar Videoclipe</button>
          <button style={{
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.14)',
            color: '#fff', borderRadius: '12px',
            padding: '16px 38px', fontSize: '16px', fontWeight: 500,
            cursor: 'pointer', transition: 'all 0.3s'
          }}
            onMouseEnter={e => { e.target.style.background = 'rgba(255,255,255,0.09)'; }}
            onMouseLeave={e => { e.target.style.background = 'rgba(255,255,255,0.05)'; }}
          >▶ Ver Exemplos</button>
        </div>

        <div style={{
          display: 'flex', gap: '56px', justifyContent: 'center', marginTop: '72px',
          opacity: visible ? 1 : 0, transition: 'all 0.8s ease 0.5s'
        }}>
          {[
            { value: '10K+', label: 'Videoclips Gerados' },
            { value: '2 min', label: 'Tempo Médio' },
            { value: '4K', label: 'Resolução Máx.' }
          ].map((s, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '30px', fontFamily: "'Bebas Neue', sans-serif", letterSpacing: '2px', color: '#f97316' }}>{s.value}</div>
              <div style={{ fontSize: '12px', color: '#4b5563', marginTop: '4px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function SectionHeader({ tag, title, sub }) {
  return (
    <div style={{ textAlign: 'center', marginBottom: '64px' }}>
      <span style={{ fontSize: '12px', color: '#f97316', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase' }}>{tag}</span>
      <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 'clamp(36px, 5vw, 52px)', letterSpacing: '3px', marginTop: '10px', color: '#fff' }}>{title}</h2>
      {sub && <p style={{ color: '#6b7280', fontSize: '16px', maxWidth: '500px', margin: '14px auto 0', lineHeight: 1.6 }}>{sub}</p>}
    </div>
  )
}

function HowItWorks() {
  return (
    <section style={{ padding: '120px 40px', background: '#070710' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        <SectionHeader tag="Processo" title="COMO FUNCIONA" sub="6 etapas automáticas da IA para criar seu videoclipe profissional do início ao fim" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{
              background: 'linear-gradient(145deg, rgba(16,16,24,1) 0%, rgba(12,12,18,1) 100%)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '18px', padding: '30px',
              position: 'relative', overflow: 'hidden',
              transition: 'all 0.35s ease', cursor: 'default'
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = s.color + '55'; e.currentTarget.style.transform = 'translateY(-3px)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: `linear-gradient(90deg, transparent 0%, ${s.color} 50%, transparent 100%)` }} />
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '12px',
                  background: `${s.color}12`, border: `1px solid ${s.color}25`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px'
                }}>{s.icon}</div>
                <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '13px', letterSpacing: '2px', color: s.color }}>{s.step}</span>
              </div>
              <h3 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '21px', letterSpacing: '1px', color: '#fff', marginBottom: '8px' }}>{s.title}</h3>
              <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: 1.65 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Features() {
  return (
    <section style={{ padding: '120px 40px', background: '#0a0a0e' }}>
      <div style={{ maxWidth: '1050px', margin: '0 auto' }}>
        <SectionHeader tag="Recursos" title="O QUE VOCÊ CONSEGUE" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '18px' }}>
          {FEATURES.map((f, i) => (
            <div key={i} style={{
              display: 'flex', gap: '20px', alignItems: 'flex-start',
              background: 'rgba(16,16,24,0.7)', border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '16px', padding: '26px',
              transition: 'all 0.3s ease'
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.25)'; e.currentTarget.style.background = 'rgba(16,16,24,0.95)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.background = 'rgba(16,16,24,0.7)'; }}
            >
              <div style={{
                width: '48px', height: '48px', minWidth: '48px', borderRadius: '14px',
                background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px'
              }}>{f.icon}</div>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginBottom: '5px' }}>{f.title}</h3>
                <p style={{ fontSize: '13px', color: '#6b7280', lineHeight: 1.7 }}>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Pricing({ onGetStarted }) {
  return (
    <section style={{ padding: '120px 40px', background: '#070710' }}>
      <div style={{ maxWidth: '960px', margin: '0 auto' }}>
        <SectionHeader tag="Preços" title="PLANOS SIMPLES" sub="Comece grátis e escale conforme sua necessidade. Sem taxas ocultas." />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          {PLANS.map((plan, i) => (
            <div key={i} style={{
              background: plan.highlight
                ? 'linear-gradient(160deg, rgba(249,115,22,0.07) 0%, rgba(14,14,20,1) 60%)'
                : 'rgba(16,16,24,0.6)',
              border: plan.highlight ? '1px solid rgba(249,115,22,0.35)' : '1px solid rgba(255,255,255,0.06)',
              borderRadius: '22px', padding: '38px 26px', textAlign: 'center',
              position: 'relative', transition: 'all 0.3s ease'
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              {plan.highlight && (
                <div style={{
                  position: 'absolute', top: '-13px', left: '50%', transform: 'translateX(-50%)',
                  background: 'linear-gradient(135deg, #f97316, #ea580c)',
                  color: '#fff', fontSize: '11px', fontWeight: 700, letterSpacing: '1.5px',
                  padding: '5px 18px', borderRadius: '12px', textTransform: 'uppercase', whiteSpace: 'nowrap'
                }}>⭐ Mais Popular</div>
              )}
              <h3 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '22px', letterSpacing: '2px', color: '#fff', marginBottom: '6px' }}>{plan.name}</h3>
              <p style={{ fontSize: '12px', color: '#4b5563', marginBottom: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>{plan.sub}</p>
              <div style={{ marginBottom: '6px' }}>
                <span style={{ fontSize: '44px', fontFamily: "'Bebas Neue', sans-serif", color: plan.highlight ? '#f97316' : '#fff', letterSpacing: '1px' }}>{plan.price}</span>
                {plan.price !== 'Grátis' && <span style={{ fontSize: '14px', color: '#4b5563' }}>/mês</span>}
              </div>
              <p style={{ fontSize: '13px', color: '#6b7280', marginBottom: '24px' }}>{plan.videos}</p>
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: '20px', marginBottom: '28px', textAlign: 'left' }}>
                {plan.features.map((f, j) => (
                  <div key={j} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '7px 0' }}>
                    <span style={{ color: '#f97316', fontSize: '13px', fontWeight: 700 }}>✓</span>
                    <span style={{ fontSize: '13px', color: '#8a929e' }}>{f}</span>
                  </div>
                ))}
              </div>
              <button onClick={onGetStarted} style={{
                width: '100%',
                background: plan.highlight ? 'linear-gradient(135deg, #f97316, #ea580c)' : 'rgba(255,255,255,0.07)',
                color: '#fff', border: plan.highlight ? 'none' : '1px solid rgba(255,255,255,0.12)',
                borderRadius: '10px', padding: '13px', fontSize: '14px', fontWeight: 600,
                cursor: 'pointer', transition: 'all 0.3s',
                boxShadow: plan.highlight ? '0 4px 18px rgba(249,115,22,0.3)' : 'none'
              }}
                onMouseEnter={e => { e.target.style.opacity = '0.85'; }}
                onMouseLeave={e => { e.target.style.opacity = '1'; }}
              >{plan.cta}</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function BottomCTA({ onGetStarted }) {
  return (
    <section style={{ padding: '100px 40px', background: 'linear-gradient(135deg, rgba(249,115,22,0.06) 0%, #0a0a0e 50%, rgba(6,182,212,0.04) 100%)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(249,115,22,0.07) 0%, transparent 65%)', pointerEvents: 'none' }} />
      <div style={{ maxWidth: '680px', margin: '0 auto', textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 'clamp(40px, 6vw, 58px)', letterSpacing: '3px', color: '#fff', marginBottom: '14px' }}>
          PRONTO PARA CRIAR?
        </h2>
        <p style={{ color: '#6b7280', fontSize: '17px', marginBottom: '36px', lineHeight: 1.6 }}>
          Comece a gerar videoclipes profissionais agora mesmo.<br />Sem cartão de crédito necessário.
        </p>
        <button onClick={onGetStarted} style={{
          background: 'linear-gradient(135deg, #f97316, #ea580c)',
          color: '#fff', border: 'none', borderRadius: '14px',
          padding: '18px 48px', fontSize: '17px', fontWeight: 600,
          cursor: 'pointer', transition: 'all 0.3s',
          boxShadow: '0 6px 28px rgba(249,115,22,0.4)'
        }}
          onMouseEnter={e => { e.target.style.transform = 'translateY(-2px)'; e.target.style.boxShadow = '0 10px 36px rgba(249,115,22,0.55)'; }}
          onMouseLeave={e => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 6px 28px rgba(249,115,22,0.4)'; }}
        >🎬 Começar Grátis Agora</button>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '44px 40px', background: '#070710' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
        <Logo size={22} />
        <p style={{ fontSize: '13px', color: '#3b4049' }}>© 2026 ClipVox. Todos os direitos reservados.</p>
        <div style={{ display: 'flex', gap: '24px' }}>
          {['Termos', 'Privacidade', 'Contato'].map(item => (
            <a key={item} style={{ color: '#4b5563', fontSize: '13px', textDecoration: 'none', cursor: 'pointer', transition: 'color 0.3s' }}
              onMouseEnter={e => e.target.style.color = '#f97316'}
              onMouseLeave={e => e.target.style.color = '#4b5563'}
            >{item}</a>
          ))}
        </div>
      </div>
    </footer>
  )
}

// ─── EXPORT PRINCIPAL ─────────────────────────────────────────
export default function Landing({ onGetStarted }) {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: '#0a0a0e', color: '#fff', minHeight: '100vh', overflowX: 'hidden' }}>
      <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&display=swap" rel="stylesheet" />
      <style>{`
        @keyframes barPulse {
          0%, 100% { transform: scaleY(0.18); }
          50% { transform: scaleY(1); }
        }
        @keyframes glowDot {
          0%, 100% { opacity: 0.5; box-shadow: 0 0 6px rgba(249,115,22,0.4); }
          50% { opacity: 1; box-shadow: 0 0 12px rgba(249,115,22,0.7); }
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #070710; }
        ::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }
      `}</style>

      <Navbar scrolled={scrolled} onGetStarted={onGetStarted} />
      <Hero onGetStarted={onGetStarted} />
      <HowItWorks />
      <Features />
      <Pricing onGetStarted={onGetStarted} />
      <BottomCTA onGetStarted={onGetStarted} />
      <Footer />
    </div>
  )
}
