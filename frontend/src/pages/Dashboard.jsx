import { useState, useEffect, useRef } from 'react'

// ─── API CONFIG ───────────────────────────────────────────────
const API_URL = 'https://clipvox-backend.onrender.com'

// ─── CSS GLOBAL ───────────────────────────────────────────────
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
  @keyframes shimmer { 0%{background-position:-1000px 0} 100%{background-position:1000px 0} }
  .skeleton {
    background: linear-gradient(90deg, rgba(255,255,255,.03) 25%, rgba(255,255,255,.08) 50%, rgba(255,255,255,.03) 75%);
    background-size: 1000px 100%;
    animation: shimmer 2s infinite;
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
  const [file,       setFile]       = useState(null)
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
    if (f && /^audio\//.test(f.type)) setFile(f)
  }

  return (
    <div style={{ maxWidth:680, margin:'0 auto', padding:'44px 24px' }}>
      <h1 style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:30, letterSpacing:2, color:'#fff', marginBottom:4 }}>NOVO VIDEOCLIPE</h1>
      <p style={{ color:'#6b7280', fontSize:13, marginBottom:28 }}>Faça upload da sua música e configure o estilo desejado</p>

      <div
        onClick={() => fileRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); accept(e.dataTransfer.files[0]) }}
        style={{
          border: dragging ? '2px dashed #f97316' : file ? '2px dashed rgba(249,115,22,.5)' : '2px dashed rgba(255,255,255,.12)',
          borderRadius:18, padding:'44px 20px', textAlign:'center', cursor:'pointer',
          background: dragging ? 'rgba(249,115,22,.05)' : 'rgba(16,16,24,.6)',
          transition:'all .3s', marginBottom:22
        }}
      >
        <input ref={fileRef} type="file" accept="audio/*" style={{ display:'none' }} onChange={e => accept(e.target.files[0])} />
        {file ? (
          <>
            <div style={{ fontSize:34, marginBottom:8 }}>🎵</div>
            <div style={{ color:'#fff', fontWeight:600, fontSize:15 }}>{file.name}</div>
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

      <button
        onClick={() => file && onStart({ file, desc, style })}
        style={{
          width:'100%', padding:'15px',
          background: file ? 'linear-gradient(135deg,#f97316,#ea580c)' : 'rgba(60,60,70,.5)',
          color:'#fff', border:'none', borderRadius:14,
          fontSize:15, fontWeight:600, cursor: file ? 'pointer' : 'not-allowed',
          boxShadow: file ? '0 4px 20px rgba(249,115,22,.35)' : 'none',
          transition:'all .25s'
        }}
        onMouseEnter={e => file && (e.target.style.boxShadow='0 6px 28px rgba(249,115,22,.5)')}
        onMouseLeave={e => file && (e.target.style.boxShadow='0 4px 20px rgba(249,115,22,.35)')}
      >
        {file ? '🎬 Gerar Videoclipe' : 'Selecione um arquivo primeiro'}
      </button>
    </div>
  )
}

// ─── LEFT PANEL ───────────────────────────────────────────────
function LeftPanel({ fileName, jobStatus, onReset }) {
  const steps = ['plan', 'analyzing', 'creative', 'scenes', 'segments', 'merge']
  const stepLabels = {
    plan: 'Plan',
    analyzing: 'Input Analyzing',
    creative: 'Creative Concept',
    scenes: 'Scenes',
    segments: 'Video Segments',
    merge: 'Merge Final'
  }

  return (
    <div style={{ width:310, minWidth:280, display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:18 }}>
        <div style={{ display:'flex', alignItems:'center', gap:14 }}>
          <div style={{ width:42, height:42, borderRadius:11, background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.2)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18 }}>🎵</div>
          <div>
            <div style={{ color:'#fff', fontSize:14, fontWeight:600 }}>{fileName}</div>
            <div style={{ color:'#4b5563', fontSize:11, marginTop:2 }}>
              {jobStatus?.audio_duration ? `${Math.floor(jobStatus.audio_duration / 60)}:${String(Math.floor(jobStatus.audio_duration % 60)).padStart(2, '0')}` : '...'}
              {jobStatus?.audio_bpm && ` · ${Math.round(jobStatus.audio_bpm)} BPM`}
            </div>
          </div>
        </div>
      </div>

      <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:'20px 18px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:18 }}>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:14, letterSpacing:2, color:'#fff' }}>📋 PLANNED STEPS</span>
        </div>
        {steps.map((step, i) => {
          const done = jobStatus?.status === 'completed' || (jobStatus?.current_step && steps.indexOf(jobStatus.current_step) > i)
          const active = jobStatus?.current_step === step
          return (
            <div key={step} style={{ display:'flex', alignItems:'center', gap:12, padding:'9px 0', borderBottom: i < steps.length-1 ? '1px solid rgba(255,255,255,.045)' : 'none' }}>
              <div style={{
                width:26, height:26, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center',
                background: done ? 'rgba(34,197,94,.15)' : active ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)',
                border:     done ? '1px solid rgba(34,197,94,.4)'  : active ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.1)',
                fontSize:11, fontWeight:700,
                color:      done ? '#22c55e' : active ? '#f97316' : '#4b5563'
              }}>
                {done ? '✓' : i+1}
              </div>
              <span style={{ flex:1, fontSize:13, fontWeight: active ? 600 : 400, color: done ? '#6b7280' : active ? '#fff' : '#4b5563' }}>{stepLabels[step]}</span>
              {done && <span style={{ color:'#22c55e', fontSize:15 }}>✓</span>}
              {active && <span style={{ color:'#f97316', fontSize:11, animation:'pulse 1.4s ease infinite' }}>⏳</span>}
            </div>
          )
        })}
      </div>

      {jobStatus?.status === 'completed' && (
        <button onClick={onReset} style={{
          width:'100%', padding:10, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)',
          borderRadius:10, color:'#6b7280', fontSize:13, cursor:'pointer', transition:'all .2s'
        }}
          onMouseEnter={e => { e.target.style.background='rgba(255,255,255,.09)'; e.target.style.color='#fff' }}
          onMouseLeave={e => { e.target.style.background='rgba(255,255,255,.05)'; e.target.style.color='#6b7280' }}
        >🔄 Novo Videoclipe</button>
      )}
    </div>
  )
}

// ─── SCENE IMAGE COMPONENT ────────────────────────────────────
function SceneImage({ scene, index }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)

  return (
    <div
      style={{
        background:'rgba(255,255,255,.03)', border:'1px solid rgba(255,255,255,.06)',
        borderRadius:11, overflow:'hidden', cursor:'pointer', transition:'all .25s',
        animation:`fadeUp .4s ease ${index*0.04}s both`,
        position:'relative'
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(249,115,22,.3)'; e.currentTarget.style.transform='translateY(-2px)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,.06)'; e.currentTarget.style.transform='translateY(0)' }}
    >
      <div style={{ height:82, position:'relative', background:'#0a0a0e' }}>
        {!loaded && !error && (
          <div className="skeleton" style={{ width:'100%', height:'100%', position:'absolute', top:0, left:0 }} />
        )}
        
        {scene.image_url && !error ? (
          <img 
            src={scene.image_url}
            alt={`Scene ${scene.scene_number}`}
            onLoad={() => setLoaded(true)}
            onError={() => setError(true)}
            style={{ 
              width:'100%', 
              height:'100%', 
              objectFit:'cover',
              opacity: loaded ? 1 : 0,
              transition:'opacity .3s'
            }}
          />
        ) : (
          <div style={{
            width:'100%', height:'100%',
            background:`linear-gradient(135deg, rgba(${80+index*10},${40+index*5},${20+index*8},1), rgba(10,10,14,1))`,
            display:'flex', alignItems:'center', justifyContent:'center', fontSize:24
          }}>
            {scene.mood?.includes('energ') ? '⚡' : scene.mood?.includes('calm') || scene.mood?.includes('sereno') ? '🌙' : '🎬'}
          </div>
        )}
        
        <div style={{ position:'absolute', bottom:5, left:5, background:'rgba(0,0,0,.7)', borderRadius:4, padding:'2px 5px', fontSize:9, color:'#fff' }}>
          Scene {scene.scene_number}
        </div>
      </div>
      
      <div style={{ padding:'8px 9px' }}>
        <div style={{ fontSize:10, color:'#fff', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
          {scene.camera_movement}
        </div>
        <div style={{ fontSize:9, color:'#4b5563', marginTop:1 }}>
          {scene.duration_seconds}s · {scene.mood}
        </div>
      </div>
    </div>
  )
}

// ─── CANVAS SECTIONS ──────────────────────────────────────────
function CreativeConceptCard({ concept }) {
  if (!concept) return null
  
  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, animation:'fadeUp .45s ease' }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:18 }}>
        <span style={{ fontSize:18 }}>🎨</span>
        <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>CREATIVE CONCEPT</span>
      </div>

      <div style={{ marginBottom:16 }}>
        <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:6 }}>🎬 DIRECTOR'S VISION</div>
        <p style={{ color:'#9ca3af', fontSize:13, lineHeight:1.7 }}>{concept.directors_vision}</p>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10, marginBottom:16 }}>
        <div style={{ background:'rgba(255,255,255,.03)', borderRadius:10, padding:12 }}>
          <div style={{ fontSize:10, color:'#4b5563', marginBottom:3 }}>🖼️ Style</div>
          <div style={{ color:'#fff', fontSize:14, fontWeight:600 }}>{concept.primary_visual_style?.substring(0, 20)}...</div>
        </div>
      </div>

      {concept.color_palette && (
        <div style={{ marginBottom:16 }}>
          <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:8 }}>🎨 COLOR PALETTE</div>
          <div style={{ display:'flex', gap:6 }}>
            {concept.color_palette.map((c,i) => (
              <div key={i} style={{ flex:1, textAlign:'center' }}>
                <div style={{ width:'100%', height:32, background:c, borderRadius:8, marginBottom:4 }} />
                <div style={{ fontSize:9, color:'#4b5563' }}>{c}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ScenesGrid({ scenes }) {
  if (!scenes || scenes.length === 0) return null
  
  const [showAll, setShowAll] = useState(false)
  const displayScenes = showAll ? scenes : scenes.slice(0, 12)
  
  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, animation:'fadeUp .45s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:18 }}>🎬</span>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>SCENES ({scenes.length})</span>
        </div>
        {scenes.length > 12 && (
          <button 
            onClick={() => setShowAll(!showAll)}
            style={{
              background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.3)',
              borderRadius:8, padding:'6px 12px', color:'#f97316', fontSize:12, cursor:'pointer'
            }}
          >
            {showAll ? 'Mostrar Menos' : `Ver Todas (${scenes.length})`}
          </button>
        )}
      </div>
      
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(120px,1fr))', gap:10 }}>
        {displayScenes.map((sc, i) => (
          <SceneImage key={sc.scene_number} scene={sc} index={i} />
        ))}
      </div>
    </div>
  )
}

// ─── MAIN DASHBOARD ──────────────────────────────────────────
export default function Dashboard({ onBack }) {
  const [phase, setPhase]       = useState('upload')
  const [credits, setCredits]   = useState(500)
  const [jobId, setJobId]       = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [fileName, setFileName] = useState('')
  const pollRef                 = useRef()

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startGeneration = async ({ file, desc, style }) => {
    try {
      setFileName(file.name)
      setPhase('processing')
      setCredits(c => c - 100)

      const formData = new FormData()
      formData.append('audio', file)
      formData.append('description', desc)
      formData.append('style', style)

      const response = await fetch(`${API_URL}/api/videos/generate`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      setJobId(data.job_id)

      // Start polling
      pollRef.current = setInterval(async () => {
        const statusRes = await fetch(`${API_URL}/api/videos/status/${data.job_id}`)
        const status = await statusRes.json()
        setJobStatus(status)

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollRef.current)
        }
      }, 2000)

    } catch (error) {
      console.error('Error:', error)
      alert('Erro ao iniciar geração. Tente novamente.')
      setPhase('upload')
    }
  }

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    setPhase('upload')
    setJobId(null)
    setJobStatus(null)
    setFileName('')
  }

  if (phase === 'upload') {
    return (
      <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
        <style>{CSS}</style>
        <Navbar onBack={onBack} credits={credits} />
        <UploadZone onStart={startGeneration} />
      </div>
    )
  }

  return (
    <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
      <style>{CSS}</style>
      <Navbar onBack={onBack} credits={credits} />

      <div style={{ display:'flex', gap:22, maxWidth:1120, margin:'28px auto', padding:'0 22px' }}>
        <LeftPanel fileName={fileName} jobStatus={jobStatus} onReset={reset} />

        <div style={{ flex:1, minWidth:0 }}>
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

          {!jobStatus && (
            <div style={{
              background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)',
              borderRadius:16, padding:'56px 24px', textAlign:'center'
            }}>
              <div style={{ width:38, height:38, margin:'0 auto 14px', border:'3px solid rgba(255,255,255,.1)', borderTop:'3px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
              <p style={{ color:'#6b7280', fontSize:14 }}>Processando sua música...</p>
            </div>
          )}

          {jobStatus?.creative_concept && <CreativeConceptCard concept={jobStatus.creative_concept} />}
          {jobStatus?.scenes && <div style={{ marginTop:16 }}><ScenesGrid scenes={jobStatus.scenes} /></div>}

          {jobStatus?.status === 'completed' && (
            <div style={{
              marginTop:16,
              background:'linear-gradient(135deg, rgba(249,115,22,.06), rgba(16,16,24,.95))',
              border:'1px solid rgba(249,115,22,.2)', borderRadius:16, padding:'40px 24px',
              textAlign:'center', animation:'fadeUp .5s ease'
            }}>
              <div style={{ fontSize:46, marginBottom:14 }}>🎬</div>
              <h3 style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:24, letterSpacing:2, color:'#fff', marginBottom:6 }}>VIDEOCLIPE PRONTO!</h3>
              <p style={{ color:'#6b7280', fontSize:14, marginBottom:24 }}>
                Gerado com {jobStatus.scenes?.length || 0} cenas cinematográficas com IA!
              </p>
              <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap' }}>
                <button style={{
                  background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none',
                  borderRadius:10, padding:'11px 26px', fontSize:14, fontWeight:600, cursor:'pointer',
                  boxShadow:'0 4px 16px rgba(249,115,22,.35)'
                }}>⬇ Baixar Vídeo</button>
                <button onClick={reset} style={{
                  background:'rgba(255,255,255,.04)', color:'#6b7280', border:'1px solid rgba(255,255,255,.08)',
                  borderRadius:10, padding:'11px 26px', fontSize:14, cursor:'pointer'
                }}>🔄 Novo Vídeo</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
