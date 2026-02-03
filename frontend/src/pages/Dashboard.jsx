import { useState, useEffect, useRef, useCallback } from 'react'

// ─── CONSTANTES ───────────────────────────────────────────────
const STEPS = [
  { id: 'plan',      label: 'Plan',                icon: '🎯', dur: 2800 },
  { id: 'analyzing','label': 'Input Analyzing',   icon: '🔍', dur: 3600 },
  { id: 'creative', label: 'Creative Concept',    icon: '🎨', dur: 4200 },
  { id: 'scenes',   label: 'Scenes',              icon: '🎬', dur: 5800 },
  { id: 'segments', label: 'Video Segments',      icon: '🎥', dur: 6400 },
  { id: 'merge',    label: 'Merge Final',         icon: '✨', dur: 3200 }
]

const MOCK_SCENES = [
  { id:1,  label:'Plano médio dinâmico',  emoji:'🌅', desc:'Amanhecer na caatinga' },
  { id:2,  label:'Close-up emocional',   emoji:'🎤', desc:'Artista no microfone' },
  { id:3,  label:'Plano aéreo',          emoji:'🏜️', desc:'Vista aérea do sertão' },
  { id:4,  label:'Ângulo baixo épico',   emoji:'🤠', desc:'Vaqueiro contra o céu' },
  { id:5,  label:'Cena de ação',         emoji:'🐂', desc:'Arena de vaquejada' },
  { id:6,  label:'Plano médio lento',    emoji:'🌙', desc:'Noite no interior' },
  { id:7,  label:'Close-up detalhes',    emoji:'🎸', desc:'Mãos tocando viola' },
  { id:8,  label:'Plano geral',          emoji:'👥', desc:'Multidão na festa' },
  { id:9,  label:'Transição lenta',      emoji:'🌄', desc:'Pôr do sol dourado' },
  { id:10, label:'Ângulo criativo',      emoji:'🏆', desc:'Troféu iluminado' },
  { id:11, label:'Plano médio íntimo',   emoji:'💃', desc:'Dança forró' },
  { id:12, label:'Cena de conexão',      emoji:'💑', desc:'Casal no baile' }
]

const MOCK_SEGMENTS = [
  { id:1,  desc:'A câmera faz um zoom suave...' },
  { id:2,  desc:'O foco de lente muda para...' },
  { id:3,  desc:'A câmera recua devagar...' },
  { id:4,  desc:'Em uma transição suave...' },
  { id:5,  desc:'A cena corta e revela...' },
  { id:6,  desc:'A câmera desliza pelo...' },
  { id:7,  desc:'Um zoom lento expõe...' },
  { id:8,  desc:'Em um movimento de...' },
  { id:9,  desc:'A transição marca o...' },
  { id:10, desc:'O vaqueiro se vira e...' }
]

const PALETTE = ['#8B4513','#D2691E','#1E3A5F','#0052CC','#F5F5DC']
const PAL_NAMES = ['Marrom Sombrio','Terracota','Azul Profundo','Azul Cobalto','Creme']

const GRADIENT_SEEDS = [
  [80,40,20],[60,30,80],[20,50,80],[80,60,20],[40,20,60],[30,60,40],
  [60,20,40],[40,60,20],[70,50,30],[50,30,70],[30,50,60],[60,40,30]
]

// ─── CSS GLOBAL (injetar uma vez) ────────────────────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0a0a0e; }
  ::-webkit-scrollbar        { width:5px; }
  ::-webkit-scrollbar-track  { background:#070710; }
  ::-webkit-scrollbar-thumb  { background:#2a2a3a; border-radius:3px; }
  textarea::placeholder      { color:#4b5563; }
  @keyframes pulse  { 0%,100%{opacity:.45} 50%{opacity:1} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes fadeUp { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
`

// ─── LOGO ─────────────────────────────────────────────────────
function Logo() {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
      <svg width={22} height={22} viewBox="0 0 32 32" fill="none">
        <rect x="1"  y="9"  width="4" height="14" rx="2" fill="#f97316" opacity=".6" />
        <rect x="7"  y="5"  width="4" height="22" rx="2" fill="#f97316" opacity=".75"/>
        <rect x="13" y="11" width="4" height="10" rx="2" fill="#f97316" opacity=".55"/>
        <rect x="19" y="3"  width="4" height="26" rx="2" fill="#f97316" />
        <rect x="25" y="7"  width="4" height="18" rx="2" fill="#f97316" opacity=".7" />
      </svg>
      <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:18, letterSpacing:3, color:'#fff' }}>CLIPVOX</span>
    </div>
  )
}

// ─── NAVBAR ───────────────────────────────────────────────────
function Navbar({ onBack, credits }) {
  return (
    <nav style={{
      borderBottom:'1px solid rgba(255,255,255,.07)', padding:'14px 28px',
      display:'flex', alignItems:'center', justifyContent:'space-between',
      background:'rgba(8,8,12,.95)', backdropFilter:'blur(10px)',
      position:'sticky', top:0, zIndex:50
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:22 }}>
        <span onClick={onBack} style={{ cursor:'pointer', color:'#6b7280', fontSize:13, display:'flex', alignItems:'center', gap:5, transition:'color .2s' }}
          onMouseEnter={e=>e.currentTarget.style.color='#fff'}
          onMouseLeave={e=>e.currentTarget.style.color='#6b7280'}
        >← Voltar</span>
        <Logo />
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <div style={{
          display:'flex', alignItems:'center', gap:8,
          background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.2)',
          borderRadius:8, padding:'6px 14px'
        }}>
          <span style={{ color:'#f97316', fontSize:14 }}>💎</span>
          <span style={{ color:'#f97316', fontWeight:600, fontSize:14 }}>{credits} créditos</span>
        </div>
        <div style={{ width:34, height:34, borderRadius:'50%', background:'linear-gradient(135deg,#f97316,#ea580c)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:14, fontWeight:600, color:'#fff' }}>U</div>
      </div>
    </nav>
  )
}

// ─── UPLOAD ZONE ──────────────────────────────────────────────
function UploadZone({ onStart }) {
  const [dragging,   setDragging]   = useState(false)
  const [fileName,   setFileName]   = useState(null)
  const [desc,       setDesc]       = useState('')
  const [style,      setStyle]      = useState('realistic')
  const fileRef                     = useRef()

  const styles = [
    { id:'realistic', label:'Fotorrealista' },
    { id:'cinematic', label:'Cinemático'    },
    { id:'animated',  label:'Animado'       },
    { id:'retro',     label:'Retro'         }
  ]

  const accept = f => {
    if (f && /^audio\//.test(f.type)) setFileName(f.name)
  }

  return (
    <div style={{ maxWidth:680, margin:'0 auto', padding:'44px 24px' }}>
      {/* title */}
      <h1 style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:30, letterSpacing:2, color:'#fff', marginBottom:4 }}>NOVO VIDEOCLIPE</h1>
      <p style={{ color:'#6b7280', fontSize:13, marginBottom:28 }}>Faça upload da sua música e configure o estilo desejado</p>

      {/* drop zone */}
      <div
        onClick={() => fileRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); accept(e.dataTransfer.files[0]) }}
        style={{
          border: dragging ? '2px dashed #f97316' : fileName ? '2px dashed rgba(249,115,22,.5)' : '2px dashed rgba(255,255,255,.12)',
          borderRadius:18, padding:'44px 20px', textAlign:'center', cursor:'pointer',
          background: dragging ? 'rgba(249,115,22,.05)' : 'rgba(16,16,24,.6)',
          transition:'all .3s', marginBottom:22
        }}
      >
        <input ref={fileRef} type="file" accept="audio/*" style={{ display:'none' }} onChange={e => accept(e.target.files[0])} />
        {fileName ? (
          <>
            <div style={{ fontSize:34, marginBottom:8 }}>🎵</div>
            <div style={{ color:'#fff', fontWeight:600, fontSize:15 }}>{fileName}</div>
            <div style={{ color:'#6b7280', fontSize:12, marginTop:3 }}>Clique para trocar</div>
          </>
        ) : (
          <>
            <div style={{ fontSize:38, marginBottom:10 }}>📂</div>
            <div style={{ color:'#fff', fontWeight:600, fontSize:15, marginBottom:5 }}>Arraste sua música aqui</div>
            <div style={{ color:'#6b7280', fontSize:13, marginBottom:8 }}>ou clique para selecionar</div>
            <span style={{ background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.25)', borderRadius:6, padding:'4px 12px', color:'#f97316', fontSize:11 }}>MP3 · WAV · OGG · M4A</span>
          </>
        )}
      </div>

      {/* estilo visual */}
      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>ESTILO VISUAL</label>
      <div style={{ display:'flex', gap:8, marginBottom:22 }}>
        {styles.map(s => (
          <div key={s.id} onClick={() => setStyle(s.id)} style={{
            flex:'1 1 0', padding:'11px 8px', borderRadius:12, cursor:'pointer', textAlign:'center',
            background: style===s.id ? 'rgba(249,115,22,.1)'  : 'rgba(16,16,24,.6)',
            border:     style===s.id ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)',
            transition:'all .25s'
          }}>
            <div style={{ color: style===s.id ? '#f97316' : '#9ca3af', fontSize:13, fontWeight:500 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* descrição */}
      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>DESCRIÇÃO DO VIDEOCLIPE</label>
      <textarea
        value={desc} onChange={e => setDesc(e.target.value)} rows={3}
        placeholder="Ex: Videoclipe sobre o universo do forró nordestino, com cenas da caatinga e festa..."
        style={{
          width:'100%', padding:'13px 16px', borderRadius:12,
          background:'rgba(16,16,24,.8)', border:'1px solid rgba(255,255,255,.1)',
          color:'#fff', fontSize:13, lineHeight:1.6, resize:'vertical', outline:'none',
          fontFamily:"'DM Sans',sans-serif", marginBottom:24
        }}
        onFocus={e => e.target.style.borderColor='rgba(249,115,22,.4)'}
        onBlur={e => e.target.style.borderColor='rgba(255,255,255,.1)'}
      />

      {/* CTA */}
      <button
        onClick={() => fileName && onStart({ fileName, desc, style })}
        style={{
          width:'100%', padding:'15px',
          background: fileName ? 'linear-gradient(135deg,#f97316,#ea580c)' : 'rgba(60,60,70,.5)',
          color:'#fff', border:'none', borderRadius:14,
          fontSize:15, fontWeight:600, cursor: fileName ? 'pointer' : 'not-allowed',
          boxShadow: fileName ? '0 4px 20px rgba(249,115,22,.35)' : 'none',
          transition:'all .25s'
        }}
        onMouseEnter={e => fileName && (e.target.style.boxShadow='0 6px 28px rgba(249,115,22,.5)')}
        onMouseLeave={e => fileName && (e.target.style.boxShadow='0 4px 20px rgba(249,115,22,.35)')}
      >
        {fileName ? '🎬 Gerar Videoclipe' : 'Selecione um arquivo primeiro'}
      </button>
    </div>
  )
}

// ─── LEFT PANEL  — file card + pipeline steps ────────────────
function LeftPanel({ uploadInfo, completedSteps, currentStep, onReset }) {
  return (
    <div style={{ width:310, minWidth:280, display:'flex', flexDirection:'column', gap:16 }}>
      {/* File card */}
      <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:18 }}>
        <div style={{ display:'flex', alignItems:'center', gap:14 }}>
          <div style={{ width:42, height:42, borderRadius:11, background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.2)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18 }}>🎵</div>
          <div>
            <div style={{ color:'#fff', fontSize:14, fontWeight:600 }}>{uploadInfo.fileName}</div>
            <div style={{ color:'#4b5563', fontSize:11, marginTop:2 }}>Estilo: {uploadInfo.style} · 2:28</div>
          </div>
        </div>
      </div>

      {/* Pipeline steps */}
      <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:'20px 18px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:18 }}>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:14, letterSpacing:2, color:'#fff' }}>📋 PLANNED STEPS</span>
        </div>
        {STEPS.map((step, i) => {
          const done    = completedSteps.includes(step.id)
          const active  = currentStep === step.id
          return (
            <div key={step.id} style={{ display:'flex', alignItems:'center', gap:12, padding:'9px 0', borderBottom: i < STEPS.length-1 ? '1px solid rgba(255,255,255,.045)' : 'none' }}>
              {/* circle */}
              <div style={{
                width:26, height:26, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center',
                background: done ? 'rgba(34,197,94,.15)' : active ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)',
                border:     done ? '1px solid rgba(34,197,94,.4)'  : active ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.1)',
                fontSize:11, fontWeight:700,
                color:      done ? '#22c55e' : active ? '#f97316' : '#4b5563'
              }}>
                {done ? '✓' : i+1}
              </div>
              {/* label */}
              <span style={{ flex:1, fontSize:13, fontWeight: active ? 600 : 400, color: done ? '#6b7280' : active ? '#fff' : '#4b5563' }}>{step.label}</span>
              {/* status tail */}
              {done    && <span style={{ color:'#22c55e', fontSize:15 }}>✓</span>}
              {active  && <span style={{ color:'#f97316', fontSize:11, animation:'pulse 1.4s ease infinite' }}>⏳</span>}
            </div>
          )
        })}
      </div>

      {/* Reset button */}
      <button onClick={onReset} style={{
        width:'100%', padding:10, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)',
        borderRadius:10, color:'#6b7280', fontSize:13, cursor:'pointer', transition:'all .2s'
      }}
        onMouseEnter={e => { e.target.style.background='rgba(255,255,255,.09)'; e.target.style.color='#fff' }}
        onMouseLeave={e => { e.target.style.background='rgba(255,255,255,.05)'; e.target.style.color='#6b7280' }}
      >🔄 Novo Videoclipe</button>
    </div>
  )
}

// ─── CANVAS SECTIONS ──────────────────────────────────────────

function CreativeConceptCard() {
  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, animation:'fadeUp .45s ease' }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:18 }}>
        <span style={{ fontSize:18 }}>🎨</span>
        <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>CREATIVE CONCEPT</span>
      </div>

      {/* Director's Vision */}
      <div style={{ marginBottom:16 }}>
        <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:6 }}>🎬 DIRECTOR'S VISION</div>
        <p style={{ color:'#9ca3af', fontSize:13, lineHeight:1.7 }}>
          Este vídeo é uma celebração visual da resiliência e do triunfo do vaqueiro nordestino. Através de um enquadramento narrativo, seguiremos o ciclo do herói, desde o amanhecer solitário na caatinga até o clímax eletrizante na arena de vaquejada.
        </p>
      </div>

      {/* Style / BPM / Key pills */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10, marginBottom:16 }}>
        {[['🖼️ Style','Realistic'],['🎵 BPM','160'],['🎼 Key','Major']].map(([lbl,val],i) => (
          <div key={i} style={{ background:'rgba(255,255,255,.03)', borderRadius:10, padding:12 }}>
            <div style={{ fontSize:10, color:'#4b5563', marginBottom:3 }}>{lbl}</div>
            <div style={{ color:'#fff', fontSize:14, fontWeight:600 }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Palette */}
      <div style={{ marginBottom:16 }}>
        <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:8 }}>🎨 COLOR PALETTE</div>
        <div style={{ display:'flex', gap:6 }}>
          {PALETTE.map((c,i) => (
            <div key={i} style={{ flex:1, textAlign:'center' }}>
              <div style={{ width:'100%', height:32, background:c, borderRadius:8, marginBottom:4 }} />
              <div style={{ fontSize:9, color:'#4b5563' }}>{PAL_NAMES[i]}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Texture */}
      <div>
        <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:5 }}>✨ TEXTURE & ATMOSPHERE</div>
        <p style={{ color:'#9ca3af', fontSize:13, lineHeight:1.6 }}>Atmosfera carregada de adrenalina e poeira. Texturas táteis de couro suado, pelo animal e areia seca em contraste com o brilho polido do troféu de ouro.</p>
      </div>
    </div>
  )
}

function ScenesGrid() {
  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, animation:'fadeUp .45s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:18 }}>🎬</span>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>SCENES</span>
        </div>
        <div style={{ display:'flex', gap:5 }}>
          <div style={{ background:'rgba(255,255,255,.08)', borderRadius:6, padding:'3px 9px', color:'#6b7280', fontSize:11 }}>v1</div>
          <div style={{ background:'rgba(249,115,22,.15)', border:'1px solid rgba(249,115,22,.3)', borderRadius:6, padding:'3px 9px', color:'#f97316', fontSize:11 }}>v2</div>
        </div>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(120px,1fr))', gap:10 }}>
        {MOCK_SCENES.map((sc, i) => (
          <div key={sc.id} style={{
            background:'rgba(255,255,255,.03)', border:'1px solid rgba(255,255,255,.06)',
            borderRadius:11, overflow:'hidden', cursor:'pointer', transition:'all .25s',
            animation:`fadeUp .4s ease ${i*0.06}s both`
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(249,115,22,.3)'; e.currentTarget.style.transform='translateY(-2px)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,.06)'; e.currentTarget.style.transform='translateY(0)' }}
          >
            <div style={{
              height:82,
              background:`linear-gradient(135deg, rgba(${GRADIENT_SEEDS[i].join(',')},1), rgba(10,10,14,1))`,
              display:'flex', alignItems:'center', justifyContent:'center', fontSize:24,
              position:'relative'
            }}>
              {sc.emoji}
              <div style={{ position:'absolute', bottom:5, left:5, background:'rgba(0,0,0,.6)', borderRadius:4, padding:'2px 5px', fontSize:9, color:'#fff' }}>Scene {sc.id}</div>
            </div>
            <div style={{ padding:'8px 9px' }}>
              <div style={{ fontSize:10, color:'#fff', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{sc.label}</div>
              <div style={{ fontSize:9, color:'#4b5563', marginTop:1 }}>{sc.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function VideoSegmentsGrid() {
  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, animation:'fadeUp .45s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:18 }}>🎥</span>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>VIDEO SEGMENTS</span>
        </div>
        <div style={{ background:'rgba(34,197,94,.1)', border:'1px solid rgba(34,197,94,.25)', borderRadius:6, padding:'3px 9px', color:'#22c55e', fontSize:11 }}>
          Generated ({MOCK_SEGMENTS.length})
        </div>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(130px,1fr))', gap:10 }}>
        {MOCK_SEGMENTS.map((seg, i) => (
          <div key={seg.id} style={{
            background:'rgba(255,255,255,.03)', border:'1px solid rgba(255,255,255,.06)',
            borderRadius:11, overflow:'hidden', cursor:'pointer', transition:'all .25s',
            animation:`fadeUp .4s ease ${i*0.07}s both`
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(249,115,22,.3)'; e.currentTarget.style.transform='translateY(-2px)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,.06)'; e.currentTarget.style.transform='translateY(0)' }}
          >
            <div style={{
              height:88,
              background:`linear-gradient(145deg, rgba(${GRADIENT_SEEDS[i % GRADIENT_SEEDS.length].join(',')},1), rgba(10,10,14,1))`,
              display:'flex', alignItems:'center', justifyContent:'center', position:'relative'
            }}>
              {/* play btn */}
              <div style={{
                width:34, height:34, borderRadius:'50%',
                background:'rgba(249,115,22,.85)', display:'flex', alignItems:'center', justifyContent:'center',
                fontSize:13, boxShadow:'0 2px 12px rgba(249,115,22,.4)'
              }}>▶</div>
              <div style={{ position:'absolute', top:5, left:5, background:'rgba(0,0,0,.6)', borderRadius:4, padding:'2px 5px', fontSize:9, color:'#fff' }}>Video {seg.id}</div>
            </div>
            <div style={{ padding:'8px 9px' }}>
              <div style={{ fontSize:10, color:'#9ca3af', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{seg.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MergeFinalCard({ onReset }) {
  return (
    <div style={{
      background:'linear-gradient(135deg, rgba(249,115,22,.06), rgba(16,16,24,.95))',
      border:'1px solid rgba(249,115,22,.2)', borderRadius:16, padding:'40px 24px',
      textAlign:'center', animation:'fadeUp .5s ease'
    }}>
      <div style={{ fontSize:46, marginBottom:14 }}>🎬</div>
      <h3 style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:24, letterSpacing:2, color:'#fff', marginBottom:6 }}>VIDEOCLIPE PRONTO!</h3>
      <p style={{ color:'#6b7280', fontSize:14, marginBottom:24 }}>Seu videoclipe foi gerado com sucesso. Baixe ou compartilhe agora!</p>
      <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap' }}>
        <button style={{
          background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none',
          borderRadius:10, padding:'11px 26px', fontSize:14, fontWeight:600, cursor:'pointer',
          boxShadow:'0 4px 16px rgba(249,115,22,.35)'
        }}>⬇ Baixar Vídeo</button>
        <button style={{
          background:'rgba(255,255,255,.06)', color:'#fff', border:'1px solid rgba(255,255,255,.12)',
          borderRadius:10, padding:'11px 26px', fontSize:14, fontWeight:500, cursor:'pointer'
        }}>📱 Compartilhar</button>
        <button onClick={onReset} style={{
          background:'rgba(255,255,255,.04)', color:'#6b7280', border:'1px solid rgba(255,255,255,.08)',
          borderRadius:10, padding:'11px 26px', fontSize:14, cursor:'pointer'
        }}>🔄 Novo Vídeo</button>
      </div>
    </div>
  )
}

// ─── MAIN DASHBOARD ──────────────────────────────────────────
export default function Dashboard({ onBack }) {
  const [phase, setPhase]               = useState('upload')   // upload | processing | done
  const [credits, setCredits]           = useState(500)
  const [currentStep, setCurrentStep]   = useState(null)
  const [completedSteps, setCompleted]  = useState([])
  const [uploadInfo, setUploadInfo]     = useState(null)
  const timersRef                       = useRef([])

  // cleanup
  useEffect(() => () => timersRef.current.forEach(clearTimeout), [])

  const startPipeline = useCallback((info) => {
    setUploadInfo(info)
    setPhase('processing')
    setCredits(c => c - 100)
    setCompleted([])

    let delay = 0
    STEPS.forEach((step, i) => {
      const t1 = setTimeout(() => setCurrentStep(step.id), delay)
      timersRef.current.push(t1)
      delay += step.dur
      const t2 = setTimeout(() => {
        setCompleted(prev => [...prev, step.id])
        if (i === STEPS.length - 1) {
          setTimeout(() => setPhase('done'), 700)
        }
      }, delay)
      timersRef.current.push(t2)
    })
  }, [])

  const reset = () => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
    setPhase('upload')
    setCurrentStep(null)
    setCompleted([])
    setUploadInfo(null)
  }

  // ── derive visibility ──
  const showCreative = completedSteps.includes('creative') || ['scenes','segments','merge'].includes(currentStep) || phase==='done'
  const showScenes   = completedSteps.includes('scenes')   || ['segments','merge'].includes(currentStep)          || phase==='done'
  const showSegments = completedSteps.includes('segments') || currentStep==='merge'                                || phase==='done'
  const showMerge    = phase === 'done'

  // ── UPLOAD ──
  if (phase === 'upload') {
    return (
      <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
        <style>{CSS}</style>
        <Navbar onBack={onBack} credits={credits} />
        <UploadZone onStart={startPipeline} />
      </div>
    )
  }

  // ── PROCESSING / DONE ──
  return (
    <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
      <style>{CSS}</style>
      <Navbar onBack={onBack} credits={credits} />

      <div style={{ display:'flex', gap:22, maxWidth:1120, margin:'28px auto', padding:'0 22px' }}>
        {/* LEFT */}
        <LeftPanel uploadInfo={uploadInfo} completedSteps={completedSteps} currentStep={currentStep} onReset={reset} />

        {/* RIGHT — Canvas */}
        <div style={{ flex:1, minWidth:0 }}>
          {/* tabs */}
          <div style={{ display:'flex', gap:6, marginBottom:18 }}>
            {['Results','Canvas'].map((tab,i) => (
              <div key={tab} style={{
                padding:'7px 16px', borderRadius:8, fontSize:13, fontWeight:500, cursor:'pointer',
                background: i===1 ? 'rgba(249,115,22,.1)' : 'rgba(255,255,255,.04)',
                border:     i===1 ? '1px solid rgba(249,115,22,.25)' : '1px solid rgba(255,255,255,.06)',
                color:      i===1 ? '#f97316' : '#6b7280'
              }}>{tab}</div>
            ))}
          </div>

          {/* spinner placeholder while waiting for Creative Concept */}
          {!showCreative && (
            <div style={{
              background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)',
              borderRadius:16, padding:'56px 24px', textAlign:'center'
            }}>
              <div style={{ width:38, height:38, margin:'0 auto 14px', border:'3px solid rgba(255,255,255,.1)', borderTop:'3px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
              <p style={{ color:'#6b7280', fontSize:14 }}>Processando sua música...</p>
            </div>
          )}

          {showCreative  && <CreativeConceptCard />}
          {showScenes    && <div style={{ marginTop:16 }}><ScenesGrid /></div>}
          {showSegments  && <div style={{ marginTop:16 }}><VideoSegmentsGrid /></div>}
          {showMerge     && <div style={{ marginTop:16 }}><MergeFinalCard onReset={reset} /></div>}
        </div>
      </div>
    </div>
  )
}
