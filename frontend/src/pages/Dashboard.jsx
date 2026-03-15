import { useState, useEffect, useRef } from 'react'

const API_URL = 'https://clipvox-backend.onrender.com'

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

function Navbar({ onBack, credits }) {
  return (
    <nav style={{
      borderBottom:'1px solid rgba(255,255,255,.07)', padding:'14px 28px',
      display:'flex', alignItems:'center', justifyContent:'space-between',
      background:'rgba(8,8,12,.95)', backdropFilter:'blur(10px)',
      position:'sticky', top:0, zIndex:50
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:22 }}>
        <span onClick={onBack} style={{ cursor:'pointer', color:'#6b7280', fontSize:13, display:'flex', alignItems:'center', gap:5 }}
          onMouseEnter={e=>e.currentTarget.style.color='#fff'}
          onMouseLeave={e=>e.currentTarget.style.color='#6b7280'}
        >← Voltar</span>
        <Logo />
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8, background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.2)', borderRadius:8, padding:'6px 14px' }}>
          <span style={{ color:'#f97316', fontSize:14 }}>💎</span>
          <span style={{ color:'#f97316', fontWeight:600, fontSize:14 }}>{credits} créditos</span>
        </div>
        <div style={{ width:34, height:34, borderRadius:'50%', background:'linear-gradient(135deg,#f97316,#ea580c)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:14, fontWeight:600, color:'#fff' }}>U</div>
      </div>
    </nav>
  )
}

function ResumeJobBox({ onResume }) {
  const [jobId, setJobId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleResume = async () => {
    const id = jobId.trim()
    if (!id) return
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/api/videos/status/${id}`)
      if (!res.ok) throw new Error('Job não encontrado')
      const data = await res.json()
      onResume(id, data)
    } catch(e) {
      setError(e.message || 'Erro ao buscar job')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth:780, margin:'0 auto', padding:'0 24px 40px' }}>
      <div style={{ background:'rgba(16,16,24,.7)', border:'1px solid rgba(255,255,255,.07)', borderRadius:14, padding:'18px 20px' }}>
        <div style={{ color:'#6b7280', fontSize:12, fontWeight:600, letterSpacing:.5, marginBottom:10 }}>🔁 RETOMAR JOB EXISTENTE</div>
        <div style={{ display:'flex', gap:8 }}>
          <input
            value={jobId} onChange={e => setJobId(e.target.value)}
            placeholder="Cole o Job ID aqui (ex: 866533e9-c529-...)"
            style={{ flex:1, padding:'10px 14px', borderRadius:10, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:12, outline:'none', fontFamily:"'DM Sans',sans-serif" }}
            onKeyDown={e => e.key === 'Enter' && handleResume()}
          />
          <button onClick={handleResume} disabled={loading || !jobId.trim()}
            style={{ padding:'10px 18px', background: jobId.trim() ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)', border:`1px solid ${jobId.trim() ? 'rgba(249,115,22,.4)' : 'rgba(255,255,255,.08)'}`, borderRadius:10, color: jobId.trim() ? '#f97316' : '#4b5563', fontSize:13, fontWeight:600, cursor: jobId.trim() ? 'pointer' : 'not-allowed', whiteSpace:'nowrap' }}>
            {loading ? '⏳' : '▶ Retomar'}
          </button>
        </div>
        {error && <div style={{ color:'#ef4444', fontSize:11, marginTop:8 }}>❌ {error}</div>}
        <div style={{ color:'#374151', fontSize:10, marginTop:8 }}>O Job ID aparece na URL ou foi exibido no início da geração</div>
      </div>
    </div>
  )
}

function UploadZone({ onStart }) {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [desc, setDesc] = useState('')
  const [style, setStyle] = useState('realistic')
  const [duration, setDuration] = useState('full')
  const [customDur, setCustomDur] = useState(30)
  const [aspectRatio, setAspectRatio] = useState('16:9')
  const [resolution, setResolution] = useState('720p')
  const [refImages, setRefImages] = useState([])    // até 3 fotos
  const [refPreviews, setRefPreviews] = useState([])
  const fileRef = useRef()
  const imageRefs = [useRef(), useRef(), useRef()]

  const styles = [
    { id:'realistic', label:'Fotorrealista', emoji:'📷' },
    { id:'cinematic', label:'Cinemático', emoji:'🎬' },
    { id:'animated', label:'Animado 3D', emoji:'🎨' },
    { id:'retro', label:'Retro 80s', emoji:'📺' },
    { id:'anime', label:'Anime', emoji:'🇯🇵' },
    { id:'cyberpunk', label:'Cyberpunk', emoji:'🌃' },
    { id:'fantasy', label:'Fantasia', emoji:'🧙' },
    { id:'minimalist', label:'Minimalista', emoji:'⬜' },
    { id:'vintage', label:'Vintage', emoji:'📽️' },
    { id:'oil_painting', label:'Pintura Óleo', emoji:'🖼️' }
  ]

  const durations = [
    { value:'10', label:'10s' }, { value:'15', label:'15s' }, { value:'30', label:'30s' },
    { value:'60', label:'1min' }, { value:'120', label:'2min' },
    { value:'full', label:'Completo' }, { value:'custom', label:'Personalizado' }
  ]

  const aspectRatios = [
    { value:'16:9', label:'Horizontal', desc:'1920×1080' },
    { value:'9:16', label:'Vertical', desc:'1080×1920' },
    { value:'1:1', label:'Quadrado', desc:'1080×1080' },
    { value:'4:3', label:'Clássico', desc:'1440×1080' }
  ]

  const resolutions = [
    { value:'720p', label:'720p', desc:'Rápido' },
    { value:'1080p', label:'1080p', desc:'Premium' }
  ]

  const acceptAudio = f => {
    if (f && (/^audio\//.test(f.type) || f.type === 'application/octet-stream' || /\.(mp3|wav|ogg|m4a|flac|aac)$/i.test(f.name))) setFile(f)
  }

  const acceptImage = (f, idx) => {
    if (f && /^image\//.test(f.type)) {
      const reader = new FileReader()
      reader.onload = e => {
        setRefImages(prev => { const a=[...prev]; a[idx]=f; return a })
        setRefPreviews(prev => { const a=[...prev]; a[idx]=e.target.result; return a })
      }
      reader.readAsDataURL(f)
    }
  }
  const removeImage = idx => {
    setRefImages(prev => prev.filter((_,i)=>i!==idx))
    setRefPreviews(prev => prev.filter((_,i)=>i!==idx))
  }

  return (
    <div style={{ maxWidth:780, margin:'0 auto', padding:'44px 24px' }}>
      <h1 style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:30, letterSpacing:2, color:'#fff', marginBottom:4 }}>NOVO VIDEOCLIPE</h1>
      <p style={{ color:'#6b7280', fontSize:13, marginBottom:28 }}>Configure todos os detalhes do seu videoclipe com IA</p>

      <div onClick={() => fileRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); acceptAudio(e.dataTransfer.files[0]) }}
        style={{ border: dragging ? '2px dashed #f97316' : file ? '2px dashed rgba(249,115,22,.5)' : '2px dashed rgba(255,255,255,.12)', borderRadius:18, padding:'44px 20px', textAlign:'center', cursor:'pointer', background: dragging ? 'rgba(249,115,22,.05)' : 'rgba(16,16,24,.6)', transition:'all .3s', marginBottom:22 }}
      >
        <input ref={fileRef} type="file" accept="audio/*" style={{ display:'none' }} onChange={e => acceptAudio(e.target.files[0])} />
        {file ? (<><div style={{ fontSize:34, marginBottom:8 }}>🎵</div><div style={{ color:'#fff', fontWeight:600, fontSize:15 }}>{file.name}</div><div style={{ color:'#6b7280', fontSize:12, marginTop:3 }}>Clique para trocar</div></>) : (<><div style={{ fontSize:38, marginBottom:10 }}>📂</div><div style={{ color:'#fff', fontWeight:600, fontSize:15, marginBottom:5 }}>Arraste sua música aqui</div><div style={{ color:'#6b7280', fontSize:13, marginBottom:8 }}>ou clique para selecionar</div><span style={{ background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.25)', borderRadius:6, padding:'4px 12px', color:'#f97316', fontSize:11 }}>MP3 · WAV · OGG · M4A</span></>)}
      </div>

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>⏱️ DURAÇÃO DO VÍDEO</label>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(7,1fr)', gap:6, marginBottom:16 }}>
        {durations.map(d => (<div key={d.value} onClick={() => setDuration(d.value)} style={{ padding:'9px 6px', borderRadius:10, cursor:'pointer', textAlign:'center', background: duration===d.value ? 'rgba(249,115,22,.1)' : 'rgba(16,16,24,.6)', border: duration===d.value ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}><div style={{ color: duration===d.value ? '#f97316' : '#9ca3af', fontSize:12, fontWeight:500 }}>{d.label}</div></div>))}
      </div>
      {duration === 'custom' && (<input type="number" value={customDur} onChange={e => setCustomDur(e.target.value)} placeholder="Segundos" min="5" max="300" style={{ width:'100%', padding:'10px 14px', borderRadius:10, marginBottom:16, background:'rgba(16,16,24,.8)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:13, outline:'none' }} />)}

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>📐 PROPORÇÃO (ASPECT RATIO)</label>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, marginBottom:22 }}>
        {aspectRatios.map(ar => (<div key={ar.value} onClick={() => setAspectRatio(ar.value)} style={{ padding:'12px 10px', borderRadius:12, cursor:'pointer', textAlign:'center', background: aspectRatio===ar.value ? 'rgba(249,115,22,.1)' : 'rgba(16,16,24,.6)', border: aspectRatio===ar.value ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}><div style={{ color: aspectRatio===ar.value ? '#f97316' : '#fff', fontSize:13, fontWeight:600, marginBottom:2 }}>{ar.label}</div><div style={{ color:'#4b5563', fontSize:10 }}>{ar.desc}</div></div>))}
      </div>

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>🎥 RESOLUÇÃO</label>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:22 }}>
        {resolutions.map(res => (<div key={res.value} onClick={() => setResolution(res.value)} style={{ padding:'12px', borderRadius:12, cursor:'pointer', textAlign:'center', background: resolution===res.value ? 'rgba(249,115,22,.1)' : 'rgba(16,16,24,.6)', border: resolution===res.value ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}><div style={{ color: resolution===res.value ? '#f97316' : '#fff', fontSize:14, fontWeight:600, marginBottom:2 }}>{res.label}</div><div style={{ color:'#4b5563', fontSize:11 }}>{res.desc}</div></div>))}
      </div>

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>🎨 ESTILO VISUAL</label>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:8, marginBottom:22 }}>
        {styles.map(s => (<div key={s.id} onClick={() => setStyle(s.id)} style={{ padding:'11px 8px', borderRadius:12, cursor:'pointer', textAlign:'center', background: style===s.id ? 'rgba(249,115,22,.1)' : 'rgba(16,16,24,.6)', border: style===s.id ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}><div style={{ fontSize:22, marginBottom:3 }}>{s.emoji}</div><div style={{ color: style===s.id ? '#f97316' : '#9ca3af', fontSize:11, fontWeight:500 }}>{s.label}</div></div>))}
      </div>

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>👤 IMAGENS DE REFERÊNCIA — até 3 (Opcional)</label>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:8, marginBottom:22 }}>
        {[0,1,2].map(idx => (
          <div key={idx} onClick={() => refImages.length > idx || refImages.length === idx ? imageRefs[idx].current.click() : null}
            style={{ border: refPreviews[idx] ? '2px dashed rgba(249,115,22,.5)' : '2px dashed rgba(255,255,255,.1)', borderRadius:12, padding:'12px', textAlign:'center', cursor:'pointer', background:'rgba(16,16,24,.6)', minHeight:90, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', position:'relative', opacity: idx > refImages.length ? 0.4 : 1 }}>
            <input ref={imageRefs[idx]} type='file' accept='image/*' style={{ display:'none' }} onChange={e => acceptImage(e.target.files[0], idx)} />
            {refPreviews[idx] ? (
              <><img src={refPreviews[idx]} style={{ width:52, height:52, borderRadius:8, objectFit:'cover', marginBottom:4 }} alt={`ref${idx+1}`} />
              <div style={{ color:'#fff', fontSize:10, fontWeight:600, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', width:'100%', textAlign:'center' }}>{refImages[idx]?.name}</div>
              <button onClick={e => { e.stopPropagation(); removeImage(idx) }} style={{ position:'absolute', top:4, right:4, background:'rgba(0,0,0,.6)', border:'none', borderRadius:4, color:'#9ca3af', fontSize:10, cursor:'pointer', padding:'2px 5px' }}>✕</button></>
            ) : (
              <><div style={{ fontSize:22, marginBottom:4 }}>{idx === 0 ? '🖼️' : '+'}</div>
              <div style={{ color: idx === 0 ? '#fff' : '#6b7280', fontSize:10, fontWeight:500 }}>{idx === 0 ? 'Foto principal' : `Foto ${idx+1}`}</div></>
            )}
          </div>
        ))}
      </div>
      {refImages.length > 0 && <div style={{ color:'#6b7280', fontSize:10, marginTop:-16, marginBottom:14 }}>💡 Múltiplas fotos melhoram a consistência do rosto em todas as cenas</div>}

      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>📝 DESCRIÇÃO DO VIDEOCLIPE</label>
      <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3}
        placeholder="Ex: Videoclipe sobre o universo do forró nordestino, com cenas da caatinga e festa..."
        style={{ width:'100%', padding:'13px 16px', borderRadius:12, background:'rgba(16,16,24,.8)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:13, lineHeight:1.6, resize:'vertical', outline:'none', fontFamily:"'DM Sans',sans-serif", marginBottom:24 }}
        onFocus={e => e.target.style.borderColor='rgba(249,115,22,.4)'}
        onBlur={e => e.target.style.borderColor='rgba(255,255,255,.1)'}
      />

      <button onClick={() => file && onStart({ file, desc, style, duration: duration==='custom' ? customDur : duration, aspectRatio, resolution, refImages })}
        style={{ width:'100%', padding:'15px', background: file ? 'linear-gradient(135deg,#f97316,#ea580c)' : 'rgba(60,60,70,.5)', color:'#fff', border:'none', borderRadius:14, fontSize:15, fontWeight:600, cursor: file ? 'pointer' : 'not-allowed', boxShadow: file ? '0 4px 20px rgba(249,115,22,.35)' : 'none', transition:'all .25s' }}>
        {file ? '🎬 Gerar Videoclipe com IA' : 'Selecione um arquivo primeiro'}
      </button>
    </div>
  )
}

function LeftPanel({ fileName, jobStatus, onReset }) {
  const steps = ['plan','analyzing','creative','scenes','segments','merge']
  const stepLabels = { plan:'Plan', analyzing:'Input Analyzing', creative:'Creative Concept', scenes:'Scenes', segments:'Video Segments', merge:'Merge Final' }
  return (
    <div style={{ width:310, minWidth:280, display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:18 }}>
        <div style={{ display:'flex', alignItems:'center', gap:14 }}>
          <div style={{ width:42, height:42, borderRadius:11, background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.2)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18 }}>🎵</div>
          <div>
            <div style={{ color:'#fff', fontSize:14, fontWeight:600 }}>{fileName}</div>
            <div style={{ color:'#4b5563', fontSize:11, marginTop:2 }}>
              {jobStatus?.audio_duration ? `${Math.floor(jobStatus.audio_duration/60)}:${String(Math.floor(jobStatus.audio_duration%60)).padStart(2,'0')}` : '...'}
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
          const done   = jobStatus?.status === 'completed' || (jobStatus?.current_step && steps.indexOf(jobStatus.current_step) > i)
          const active = jobStatus?.current_step === step
          return (
            <div key={step} style={{ display:'flex', alignItems:'center', gap:12, padding:'9px 0', borderBottom: i < steps.length-1 ? '1px solid rgba(255,255,255,.045)' : 'none' }}>
              <div style={{ width:26, height:26, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', background: done ? 'rgba(34,197,94,.15)' : active ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)', border: done ? '1px solid rgba(34,197,94,.4)' : active ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.1)', fontSize:11, fontWeight:700, color: done ? '#22c55e' : active ? '#f97316' : '#4b5563' }}>
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
        <button onClick={onReset} style={{ width:'100%', padding:10, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, color:'#6b7280', fontSize:13, cursor:'pointer' }}
          onMouseEnter={e => { e.target.style.background='rgba(255,255,255,.09)'; e.target.style.color='#fff' }}
          onMouseLeave={e => { e.target.style.background='rgba(255,255,255,.05)'; e.target.style.color='#6b7280' }}>
          🔄 Novo Videoclipe
        </button>
      )}
    </div>
  )
}

function SceneImage({ scene, index }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError]   = useState(false)
  return (
    <div style={{ background:'rgba(255,255,255,.03)', border:'1px solid rgba(255,255,255,.06)', borderRadius:11, overflow:'hidden', cursor:'pointer', transition:'all .25s', animation:`fadeUp .4s ease ${index*0.04}s both`, position:'relative' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(249,115,22,.3)'; e.currentTarget.style.transform='translateY(-2px)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,.06)'; e.currentTarget.style.transform='translateY(0)' }}>
      <div style={{ height:82, position:'relative', background:'#0a0a0e' }}>
        {!loaded && !error && <div className="skeleton" style={{ width:'100%', height:'100%', position:'absolute', top:0, left:0 }} />}
        {scene.image_url && !error ? (
          <img src={scene.image_url} alt={`Scene ${scene.scene_number}`} onLoad={() => setLoaded(true)} onError={() => setError(true)} style={{ width:'100%', height:'100%', objectFit:'cover', opacity: loaded ? 1 : 0, transition:'opacity .3s' }} />
        ) : (
          <div style={{ width:'100%', height:'100%', background:`linear-gradient(135deg, rgba(${80+index*10},${40+index*5},${20+index*8},1), rgba(10,10,14,1))`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:24 }}>🎬</div>
        )}
        <div style={{ position:'absolute', bottom:5, left:5, background:'rgba(0,0,0,.7)', borderRadius:4, padding:'2px 5px', fontSize:9, color:'#fff' }}>Scene {scene.scene_number}</div>
      </div>
      <div style={{ padding:'8px 9px' }}>
        <div style={{ fontSize:10, color:'#fff', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{scene.camera_movement}</div>
        <div style={{ fontSize:9, color:'#4b5563', marginTop:1 }}>{scene.duration_seconds}s · {scene.mood}</div>
      </div>
    </div>
  )
}

function VideoClipCard({ clip, index }) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef()
  const togglePlay = () => {
    if (!videoRef.current) return
    if (playing) { videoRef.current.pause(); setPlaying(false) }
    else { videoRef.current.play(); setPlaying(true) }
  }
  if (!clip.success || !clip.video_url) {
    return (
      <div style={{ background:'rgba(239,68,68,.05)', border:'1px solid rgba(239,68,68,.15)', borderRadius:12, padding:'16px', textAlign:'center', animation:`fadeUp .4s ease ${index*0.06}s both` }}>
        <div style={{ fontSize:24, marginBottom:6 }}>❌</div>
        <div style={{ color:'#ef4444', fontSize:11, fontWeight:600 }}>Cena {clip.scene_number}</div>
        <div style={{ color:'#6b7280', fontSize:10, marginTop:2 }}>{clip.error || 'Falhou'}</div>
      </div>
    )
  }
  return (
    <div style={{ background:'rgba(16,16,24,.9)', border:'1px solid rgba(255,255,255,.08)', borderRadius:12, overflow:'hidden', animation:`fadeUp .4s ease ${index*0.06}s both`, transition:'all .25s' }}
      onMouseEnter={e => e.currentTarget.style.borderColor='rgba(249,115,22,.35)'}
      onMouseLeave={e => e.currentTarget.style.borderColor='rgba(255,255,255,.08)'}>
      <div style={{ position:'relative', background:'#000', cursor:'pointer' }} onClick={togglePlay}>
        <video ref={videoRef} src={clip.video_url} loop muted playsInline style={{ width:'100%', display:'block', maxHeight:140, objectFit:'cover' }} onEnded={() => setPlaying(false)} />
        <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', background: playing ? 'transparent' : 'rgba(0,0,0,.4)', transition:'background .2s' }}>
          {!playing && (<div style={{ width:38, height:38, borderRadius:'50%', background:'rgba(249,115,22,.9)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:14 }}>▶</div>)}
        </div>
        <div style={{ position:'absolute', top:6, left:6, background:'rgba(0,0,0,.75)', borderRadius:4, padding:'2px 7px', fontSize:9, color:'#fff', fontWeight:600 }}>CENA {clip.scene_number}</div>
        <div style={{ position:'absolute', top:6, right:6, background:'rgba(249,115,22,.8)', borderRadius:4, padding:'2px 7px', fontSize:9, color:'#fff', fontWeight:600 }}>{clip.duration}s</div>
      </div>
      <div style={{ padding:'10px 12px', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div style={{ color:'#9ca3af', fontSize:10 }}>Kling AI · {clip.mode === 'pro' ? '⭐ Pro' : 'Standard'}</div>
        <a href={clip.video_url} download={`cena_${clip.scene_number}.mp4`} target="_blank" rel="noreferrer"
          style={{ color:'#f97316', fontSize:10, textDecoration:'none', display:'flex', alignItems:'center', gap:3 }}
          onClick={e => e.stopPropagation()}>
          ⬇ Baixar
        </a>
      </div>
    </div>
  )
}

function VideoClipsPanel({ jobId, jobStatus, onVideosCompleted, onCancel }) {
  const [videosStatus, setVideosStatus] = useState(null)
  const [videoClips,   setVideoClips]   = useState(null)
  const [klingMode,    setKlingMode]    = useState('std')
  const [generating,   setGenerating]   = useState(false)
  const [error,        setError]        = useState(null)
  const pollRef = useRef()

  useEffect(() => {
    const s = jobStatus?.videos_status
    if (s === 'processing' || s === 'completed' || s === 'failed') setVideosStatus(s)
    if (jobStatus?.video_clips) {
      setVideoClips(jobStatus.video_clips)
      // ✅ Auto-notifica Dashboard se vídeos já estão prontos (recuperado do Supabase)
      if (s === 'completed' && onVideosCompleted) onVideosCompleted(jobStatus.video_clips)
    }
  }, [jobStatus])

  useEffect(() => {
    if (videosStatus === 'processing' || videosStatus === 'retrying') {
      pollRef.current = setInterval(async () => {
        try {
          const res    = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const status = await res.json()
          if (status.video_clips)   setVideoClips(status.video_clips)
          if (status.videos_status) setVideosStatus(status.videos_status)
          if (status.videos_status === 'completed' || status.videos_status === 'failed') {
            clearInterval(pollRef.current)
            setGenerating(false)
            if (onVideosCompleted) onVideosCompleted(status.video_clips)
          }
        } catch(e) { console.warn('Polling vídeos:', e) }
      }, 4000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [videosStatus, jobId])

  const handleGenerate = async () => {
    if (generating) return
    setGenerating(true); setError(null); setVideosStatus('processing')
    try {
      const controller = new AbortController()
      const tid = setTimeout(() => controller.abort(), 90000)
      const res = await fetch(`${API_URL}/api/videos/generate-clips/${jobId}?mode=${klingMode}`, { method:'POST', signal:controller.signal })
      clearTimeout(tid)
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Erro ${res.status}`) }
    } catch(err) {
      if (err.name === 'AbortError') { return }
      setError(err.message || 'Erro ao iniciar geração de vídeos')
      setGenerating(false); setVideosStatus(null)
    }
  }

  const scenes        = jobStatus?.scenes || []
  const validScenes   = scenes.filter(s => s.success)
  const totalClips    = validScenes.length
  const estimatedCost = (totalClips * (klingMode === 'std' ? 0.14 : 0.28)).toFixed(2)
  const successClips  = videoClips?.filter(c => c.success) || []
  const failedClips   = videoClips?.filter(c => !c.success || !c.video_url) || []

  const handleRetry = async () => {
    if (generating) return
    setGenerating(true); setError(null); setVideosStatus('retrying')
    try {
      const res = await fetch(`${API_URL}/api/videos/retry-clips/${jobId}?mode=${klingMode}`, { method:'POST' })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Erro ${res.status}`) }
    } catch(err) {
      setError(err.message || 'Erro ao tentar regenerar')
      setGenerating(false); setVideosStatus('completed')
    }
  }

  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, marginTop:16, animation:'fadeUp .5s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ fontSize:20 }}>🎬</span>
          <div>
            <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>SEGMENTOS DE VÍDEO</div>
            <div style={{ color:'#6b7280', fontSize:11, marginTop:1 }}>Kling AI (PiAPI) · Image-to-Video</div>
          </div>
        </div>
        {videosStatus === 'completed' && (
          <div style={{ background:'rgba(34,197,94,.1)', border:'1px solid rgba(34,197,94,.3)', borderRadius:8, padding:'4px 12px', color:'#22c55e', fontSize:11, fontWeight:600 }}>
            ✓ {successClips.length}/{totalClips} gerados
          </div>
        )}
      </div>

      {(!videosStatus || videosStatus === 'pending' || videosStatus === 'ready') && (
        <>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:16 }}>
            {[
              { value:'std', label:'Standard', price:'~$0.14/clipe', desc:'Bom para testes' },
              { value:'pro', label:'Professional', price:'~$0.28/clipe', desc:'Qualidade cinematográfica' }
            ].map(m => (
              <div key={m.value} onClick={() => setKlingMode(m.value)}
                style={{ padding:'12px 14px', borderRadius:12, cursor:'pointer', background: klingMode===m.value ? 'rgba(249,115,22,.1)' : 'rgba(255,255,255,.03)', border: klingMode===m.value ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}>
                <div style={{ color: klingMode===m.value ? '#f97316' : '#fff', fontSize:13, fontWeight:600, marginBottom:2 }}>{m.label}</div>
                <div style={{ color:'#f97316', fontSize:12, fontWeight:700, marginBottom:2 }}>{m.price}</div>
                <div style={{ color:'#6b7280', fontSize:10 }}>{m.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ background:'rgba(249,115,22,.05)', border:'1px solid rgba(249,115,22,.12)', borderRadius:10, padding:'10px 14px', marginBottom:16, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <div>
              <div style={{ color:'#f97316', fontSize:11, fontWeight:600 }}>💰 CUSTO ESTIMADO</div>
              <div style={{ color:'#6b7280', fontSize:11, marginTop:2 }}>{totalClips} clipes × {klingMode === 'std' ? '$0.14' : '$0.28'} = <span style={{ color:'#fff', fontWeight:600 }}>${estimatedCost}</span></div>
            </div>
            <div style={{ color:'#4b5563', fontSize:11 }}>{totalClips} imagens prontas</div>
          </div>
          {error && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {error}</div>)}
          <button onClick={handleGenerate}
            style={{ width:'100%', padding:'13px', background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(249,115,22,.3)', transition:'all .25s' }}>
            🎬 Gerar {totalClips} Clipes de Vídeo com Kling AI
          </button>
        </>
      )}

      {videosStatus === 'processing' && (
        <div style={{ textAlign:'center', padding:'32px 0' }}>
          <div style={{ width:44, height:44, margin:'0 auto 16px', border:'3px solid rgba(249,115,22,.2)', borderTop:'3px solid #f97316', borderRadius:'50%', animation:'spin .9s linear infinite' }} />
          <div style={{ color:'#fff', fontSize:14, fontWeight:600, marginBottom:6 }}>Gerando clipes com Kling AI...</div>
          <div style={{ color:'#6b7280', fontSize:12 }}>Cada clipe leva ~1-3 minutos • Aguarde</div>
          <div style={{ marginTop:12, color:'#f97316', fontSize:11, animation:'pulse 1.5s ease infinite' }}>⏳ Processando {totalClips} cenas</div>
          {onCancel && <button onClick={onCancel} style={{ marginTop:16, background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar</button>}
        </div>
      )}

      {videosStatus === 'completed' && videoClips && (
        <>
          {failedClips.length > 0 && (
            <div style={{ background:'rgba(234,179,8,.06)', border:'1px solid rgba(234,179,8,.2)', borderRadius:10, padding:'12px 16px', marginBottom:14, display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:8 }}>
              <div>
                <div style={{ color:'#eab308', fontSize:12, fontWeight:600, marginBottom:2 }}>⚠️ {failedClips.length} cena(s) falharam</div>
                <div style={{ color:'#6b7280', fontSize:11 }}>Cenas: {failedClips.map(c => c.scene_number).join(', ')} · Custo: ~${(failedClips.length * (klingMode === 'std' ? 0.14 : 0.28)).toFixed(2)}</div>
              </div>
              <button onClick={handleRetry}
                style={{ padding:'8px 18px', background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none', borderRadius:10, fontSize:12, fontWeight:600, cursor:'pointer' }}>
                🔄 Regenerar {failedClips.length} cena(s)
              </button>
            </div>
          )}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px,1fr))', gap:12, marginTop:4 }}>
            {videoClips.map((clip, i) => (<VideoClipCard key={clip.scene_number || i} clip={clip} index={i} />))}
          </div>
        </>
      )}

      {videosStatus === 'retrying' && (
        <div style={{ textAlign:'center', padding:'24px 0' }}>
          <div style={{ width:44, height:44, margin:'0 auto 16px', border:'3px solid rgba(234,179,8,.2)', borderTop:'3px solid #eab308', borderRadius:'50%', animation:'spin .9s linear infinite' }} />
          <div style={{ color:'#fff', fontSize:14, fontWeight:600, marginBottom:6 }}>Regenerando cenas com falha...</div>
          <div style={{ color:'#6b7280', fontSize:12 }}>Apenas as cenas que falharam • Créditos já gastos são mantidos</div>
          {onCancel && <button onClick={onCancel} style={{ marginTop:14, background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar</button>}
        </div>
      )}

      {videosStatus === 'failed' && (
        <div style={{ textAlign:'center', padding:'24px' }}>
          <div style={{ fontSize:32, marginBottom:10 }}>❌</div>
          <div style={{ color:'#ef4444', fontSize:14, fontWeight:600, marginBottom:8 }}>Erro ao gerar clipes</div>
          <button onClick={() => { setVideosStatus(null); setError(null) }}
            style={{ background:'rgba(255,255,255,.06)', color:'#fff', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'8px 20px', fontSize:13, cursor:'pointer' }}>
            🔄 Tentar novamente
          </button>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 🎤 LIP SYNC PANEL
// ══════════════════════════════════════════════════════════════════════════════
function LipSyncPanel({ jobId, videoClips, onLipSyncCompleted, initialLipSyncStatus, onCancel }) {
  // ✅ Se chegar com 'processing' do Supabase, consideramos travado (servidor reiniciou)
  const isStuck = initialLipSyncStatus === 'processing'
  const [status,    setStatus]    = useState(isStuck ? 'stuck' : null)
  const [lipUrl,    setLipUrl]    = useState(null)
  const [error,     setError]     = useState(null)
  const [model,     setModel]     = useState('kling')
  const [skipped,   setSkipped]   = useState(false)
  const [audioFile, setAudioFile] = useState(null)   // ✅ re-upload de áudio após restart
  const pollRef  = useRef()
  const audioRef = useRef()

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleStart = async () => {
    // Se stuck, exige áudio novo
    if (status === 'stuck' && !audioFile) {
      setError('O servidor foi reiniciado e o áudio foi perdido. Selecione o arquivo de áudio para refazer.')
      return
    }
    setStatus('processing'); setError(null)
    try {
      const formData = new FormData()
      formData.append('model', model)
      if (audioFile) formData.append('audio', audioFile)  // ✅ re-upload quando necessário
      const res = await fetch(`${API_URL}/api/videos/lipsync/${jobId}`, { method:'POST', body:formData })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Erro ${res.status}`) }

      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const s = await r.json()
          if (s.lipsync_status === 'completed') {
            clearInterval(pollRef.current)
            setStatus('completed')
            setLipUrl(s.lipsync_url)
            if (onLipSyncCompleted) onLipSyncCompleted(s.lipsync_url)
          } else if (s.lipsync_status === 'failed') {
            clearInterval(pollRef.current)
            setStatus('failed')
            setError(s.lipsync_error || 'Lip sync falhou')
          }
        } catch(e) { console.warn('Polling lipsync:', e) }
      }, 5000)
    } catch(err) {
      setError(err.message || 'Erro ao iniciar lip sync')
      setStatus('stuck')  // volta para stuck para permitir retry com áudio
    }
  }

  const handleSkip = () => {
    setSkipped(true)
    if (onLipSyncCompleted) onLipSyncCompleted(null)
  }

  if (skipped) return null

  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:`1px solid ${isStuck && status === 'stuck' ? 'rgba(234,179,8,.3)' : 'rgba(139,92,246,.25)'}`, borderRadius:16, padding:24, marginTop:16, animation:'fadeUp .5s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ fontSize:20 }}>🎤</span>
          <div>
            <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>LIP SYNC — SINCRONIZAÇÃO DE FALA</div>
            <div style={{ color:'#6b7280', fontSize:11, marginTop:1 }}>StemSplit + Kling AI · Vocals isolados → Boca sincronizada</div>
          </div>
        </div>
        {status !== 'stuck' && (
          <div style={{ background:'rgba(139,92,246,.1)', border:'1px solid rgba(139,92,246,.3)', borderRadius:8, padding:'4px 12px', color:'#a78bfa', fontSize:11, fontWeight:600 }}>✨ Novo</div>
        )}
      </div>

      {/* ✅ ESTADO TRAVADO — servidor reiniciou */}
      {status === 'stuck' && (
        <div style={{ marginBottom:16 }}>
          <div style={{ background:'rgba(234,179,8,.08)', border:'1px solid rgba(234,179,8,.25)', borderRadius:10, padding:'14px 16px', marginBottom:16 }}>
            <div style={{ color:'#eab308', fontSize:13, fontWeight:600, marginBottom:6 }}>⚠️ Lip sync interrompido</div>
            <div style={{ color:'#9ca3af', fontSize:12, lineHeight:1.7 }}>
              O servidor foi reiniciado durante o processamento e o arquivo de áudio foi perdido do servidor.<br/>
              <strong style={{ color:'#fff' }}>Faça upload da música novamente</strong> para refazer o lip sync — os vídeos estão salvos.
            </div>
          </div>

          {/* Upload de áudio */}
          <div onClick={() => audioRef.current.click()}
            style={{ border: audioFile ? '2px dashed rgba(139,92,246,.5)' : '2px dashed rgba(139,92,246,.25)', borderRadius:12, padding:'18px', textAlign:'center', cursor:'pointer', background:'rgba(139,92,246,.04)', marginBottom:14 }}>
            <input ref={audioRef} type="file" accept="audio/*" style={{ display:'none' }}
              onChange={e => { const f = e.target.files[0]; if (f) setAudioFile(f) }} />
            {audioFile
              ? <><div style={{ fontSize:24, marginBottom:6 }}>🎵</div><div style={{ color:'#a78bfa', fontSize:13, fontWeight:600 }}>{audioFile.name}</div><div style={{ color:'#6b7280', fontSize:11, marginTop:2 }}>Clique para trocar</div></>
              : <><div style={{ fontSize:28, marginBottom:6 }}>📂</div><div style={{ color:'#fff', fontSize:13, fontWeight:600, marginBottom:4 }}>Selecionar arquivo de áudio</div><div style={{ color:'#6b7280', fontSize:11 }}>MP3 · WAV · OGG · M4A</div></>
            }
          </div>

          {error && <div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:12, color:'#ef4444', fontSize:12 }}>❌ {error}</div>}

          <button onClick={handleStart} disabled={!audioFile}
            style={{ width:'100%', padding:'13px', background: audioFile ? 'linear-gradient(135deg,#7c3aed,#6d28d9)' : 'rgba(60,60,70,.5)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor: audioFile ? 'pointer' : 'not-allowed', boxShadow: audioFile ? '0 4px 18px rgba(124,58,237,.3)' : 'none', marginBottom:10, transition:'all .25s' }}>
            🎤 Refazer Lip Sync com novo áudio
          </button>
          <button onClick={handleSkip}
            style={{ width:'100%', padding:'10px', background:'transparent', color:'#4b5563', border:'1px solid rgba(255,255,255,.07)', borderRadius:10, fontSize:13, cursor:'pointer' }}>
            Pular — ir direto para o Merge
          </button>
        </div>
      )}

      {/* ESTADO INICIAL — normal */}
      {status === null && (
        <>
          <div style={{ background:'rgba(139,92,246,.06)', border:'1px solid rgba(139,92,246,.15)', borderRadius:10, padding:'12px 16px', marginBottom:16 }}>
            <div style={{ color:'#a78bfa', fontSize:12, fontWeight:600, marginBottom:6 }}>🧠 Como funciona:</div>
            <div style={{ color:'#9ca3af', fontSize:12, lineHeight:1.8 }}>
              1️⃣ StemSplit extrai <strong style={{color:'#fff'}}>apenas a voz</strong> da música (remove instrumentos)<br/>
              2️⃣ Kling AI sincroniza a boca do personagem com a voz limpa<br/>
              3️⃣ Resultado: <strong style={{color:'#fff'}}>lábios movendo em perfeita sincronia</strong> com a letra
            </div>
          </div>

          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:16 }}>
            {[
              { value:'kling',      label:'Kling Standard', desc:'~$0.10/5s', quality:'Bom' },
              { value:'kling-v1-5', label:'Kling v1.5',     desc:'~$0.10/5s', quality:'Excelente' }
            ].map(m => (
              <div key={m.value} onClick={() => setModel(m.value)}
                style={{ padding:'12px 14px', borderRadius:12, cursor:'pointer', background: model===m.value ? 'rgba(139,92,246,.1)' : 'rgba(255,255,255,.03)', border: model===m.value ? '1px solid rgba(139,92,246,.4)' : '1px solid rgba(255,255,255,.07)', transition:'all .25s' }}>
                <div style={{ color: model===m.value ? '#a78bfa' : '#fff', fontSize:13, fontWeight:600, marginBottom:2 }}>{m.label}</div>
                <div style={{ color:'#a78bfa', fontSize:11, fontWeight:600, marginBottom:2 }}>{m.desc}</div>
                <div style={{ color:'#6b7280', fontSize:10 }}>Qualidade: {m.quality}</div>
              </div>
            ))}
          </div>

          <div style={{ background:'rgba(139,92,246,.05)', border:'1px solid rgba(139,92,246,.12)', borderRadius:10, padding:'10px 14px', marginBottom:16 }}>
            <div style={{ color:'#a78bfa', fontSize:11, fontWeight:600 }}>⏱️ TEMPO ESTIMADO</div>
            <div style={{ color:'#6b7280', fontSize:11, marginTop:2 }}>StemSplit ~30s + Kling lip sync ~2-5min = <span style={{ color:'#fff', fontWeight:600 }}>~5-6 min no total</span></div>
          </div>

          {error && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {error}</div>)}

          <button onClick={handleStart}
            style={{ width:'100%', padding:'13px', background:'linear-gradient(135deg,#7c3aed,#6d28d9)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(124,58,237,.3)', marginBottom:10, transition:'all .25s' }}>
            🎤 Aplicar Lip Sync na Música
          </button>

          <button onClick={handleSkip}
            style={{ width:'100%', padding:'10px', background:'transparent', color:'#4b5563', border:'1px solid rgba(255,255,255,.07)', borderRadius:10, fontSize:13, cursor:'pointer', transition:'all .25s' }}>
            Pular — ir direto para o Merge
          </button>
        </>
      )}

      {status === 'processing' && (
        <div style={{ textAlign:'center', padding:'32px 0' }}>
          <div style={{ width:44, height:44, margin:'0 auto 16px', border:'3px solid rgba(139,92,246,.2)', borderTop:'3px solid #7c3aed', borderRadius:'50%', animation:'spin .9s linear infinite' }} />
          <div style={{ color:'#fff', fontSize:14, fontWeight:600, marginBottom:6 }}>Aplicando Lip Sync...</div>
          <div style={{ color:'#6b7280', fontSize:12, marginBottom:8 }}>StemSplit extraindo vocals → Kling sincronizando lábios</div>
          <div style={{ color:'#a78bfa', fontSize:11, animation:'pulse 1.5s ease infinite' }}>⏳ Aguarde ~5-6 minutos</div>
          {onCancel && <button onClick={onCancel} style={{ marginTop:16, background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar Lip Sync</button>}
        </div>
      )}

      {status === 'completed' && lipUrl && (
        <div style={{ textAlign:'center', padding:'16px 0' }}>
          <div style={{ fontSize:40, marginBottom:12 }}>🎤✨</div>
          <div style={{ color:'#a78bfa', fontSize:16, fontWeight:700, marginBottom:6 }}>Lip Sync concluído!</div>
          <div style={{ color:'#6b7280', fontSize:12, marginBottom:20 }}>Boca sincronizada com a voz da música</div>
          <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap', marginBottom:16 }}>
            <a href={lipUrl} target="_blank" rel="noreferrer"
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'linear-gradient(135deg,#7c3aed,#6d28d9)', color:'#fff', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ▶ Ver Lip Sync
            </a>
            <a href={lipUrl} download={`lipsync_${jobId}.mp4`}
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'rgba(255,255,255,.07)', color:'#fff', border:'1px solid rgba(255,255,255,.15)', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ⬇ Baixar
            </a>
          </div>
          <div style={{ color:'#4b5563', fontSize:11 }}>Agora você pode fazer o Merge com o lip sync aplicado ↓</div>
        </div>
      )}

      {status === 'failed' && (
        <div style={{ textAlign:'center', padding:'24px' }}>
          <div style={{ fontSize:32, marginBottom:10 }}>❌</div>
          <div style={{ color:'#ef4444', fontSize:14, fontWeight:600, marginBottom:8 }}>Lip Sync falhou</div>
          <div style={{ color:'#6b7280', fontSize:12, marginBottom:16 }}>{error || 'Erro desconhecido'}</div>
          <div style={{ display:'flex', gap:8, justifyContent:'center' }}>
            <button onClick={() => { setStatus(null); setError(null) }}
              style={{ background:'rgba(139,92,246,.1)', color:'#a78bfa', border:'1px solid rgba(139,92,246,.3)', borderRadius:10, padding:'8px 20px', fontSize:13, cursor:'pointer' }}>
              🔄 Tentar novamente
            </button>
            <button onClick={handleSkip}
              style={{ background:'rgba(255,255,255,.06)', color:'#fff', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'8px 20px', fontSize:13, cursor:'pointer' }}>
              Pular
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function MergePanel({ jobId, videoClips, lipSyncUrl }) {
  const [mergeStatus, setMergeStatus] = useState(null)
  const [mergeUrl,    setMergeUrl]    = useState(null)
  const [mergeError,  setMergeError]  = useState(null)
  const [loading,     setLoading]     = useState(false)
  const pollRef = useRef()

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const successClips = (videoClips || []).filter(c => c.success && c.video_url)

  const handleMerge = async () => {
    if (loading) return
    setLoading(true); setMergeError(null); setMergeStatus('processing')
    try {
      const res = await fetch(`${API_URL}/api/videos/merge/${jobId}`, { method:'POST' })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Erro ${res.status}`) }
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const s = await r.json()
          if (s.merge_status) setMergeStatus(s.merge_status)
          if (s.merge_url)    setMergeUrl(s.merge_url)
          if (s.merge_status === 'completed' || s.merge_status === 'failed') {
            clearInterval(pollRef.current); setLoading(false)
            if (s.merge_status === 'failed') setMergeError('Merge falhou. Tente novamente.')
          }
        } catch(e) { console.warn('Polling merge:', e) }
      }, 4000)
    } catch(err) {
      setMergeError(err.message || 'Erro ao iniciar merge')
      setLoading(false); setMergeStatus(null)
    }
  }

  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(34,197,94,.15)', borderRadius:16, padding:24, marginTop:16, animation:'fadeUp .5s ease' }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:20 }}>
        <span style={{ fontSize:20 }}>🎞️</span>
        <div>
          <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>MERGE FINAL</div>
          <div style={{ color:'#6b7280', fontSize:11, marginTop:1 }}>Unir {successClips.length} clipes + áudio original</div>
        </div>
      </div>

      {(!mergeStatus || mergeStatus === 'idle') && (
        <>
          <div style={{ background:'rgba(34,197,94,.05)', border:'1px solid rgba(34,197,94,.12)', borderRadius:10, padding:'12px 16px', marginBottom:16 }}>
            <div style={{ color:'#22c55e', fontSize:12, fontWeight:600, marginBottom:4 }}>📋 O que será feito:</div>
            <div style={{ color:'#9ca3af', fontSize:12, lineHeight:1.8 }}>
              ✅ {successClips.length} clipes concatenados em ordem<br/>
              {lipSyncUrl ? '🎤 Lip sync aplicado na cena principal' : '🎵 Áudio original da música adicionado'}<br/>
              📦 Vídeo final exportado em MP4
            </div>
          </div>
          {mergeError && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {mergeError}</div>)}
          <button onClick={handleMerge}
            style={{ width:'100%', padding:'14px', background:'linear-gradient(135deg,#22c55e,#16a34a)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(34,197,94,.3)', transition:'all .25s' }}>
            🎬 Gerar Videoclipe Final
          </button>
        </>
      )}

      {mergeStatus === 'processing' && (
        <div style={{ textAlign:'center', padding:'32px 0' }}>
          <div style={{ width:44, height:44, margin:'0 auto 16px', border:'3px solid rgba(34,197,94,.2)', borderTop:'3px solid #22c55e', borderRadius:'50%', animation:'spin .9s linear infinite' }} />
          <div style={{ color:'#fff', fontSize:14, fontWeight:600, marginBottom:6 }}>Gerando videoclipe final...</div>
          <div style={{ color:'#6b7280', fontSize:12 }}>Concatenando clipes e adicionando áudio</div>
          <div style={{ marginTop:10, color:'#22c55e', fontSize:11, animation:'pulse 1.5s ease infinite' }}>⏳ Isso pode levar 2-5 minutos</div>
        </div>
      )}

      {mergeStatus === 'completed' && mergeUrl && (
        <div style={{ textAlign:'center', padding:'16px 0' }}>
          <div style={{ fontSize:40, marginBottom:12 }}>🎉</div>
          <div style={{ color:'#22c55e', fontSize:16, fontWeight:700, marginBottom:6 }}>Videoclipe pronto!</div>
          <div style={{ color:'#6b7280', fontSize:12, marginBottom:20 }}>Seu videoclipe foi gerado com sucesso</div>
          <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap' }}>
            <a href={mergeUrl} target="_blank" rel="noreferrer"
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'linear-gradient(135deg,#22c55e,#16a34a)', color:'#fff', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ▶ Assistir Vídeo
            </a>
            <a href={mergeUrl} download={`clipvox_${jobId}.mp4`}
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'rgba(255,255,255,.07)', color:'#fff', border:'1px solid rgba(255,255,255,.15)', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ⬇ Baixar MP4
            </a>
          </div>
        </div>
      )}

      {mergeStatus === 'failed' && (
        <div style={{ textAlign:'center', padding:'24px' }}>
          <div style={{ fontSize:32, marginBottom:10 }}>❌</div>
          <div style={{ color:'#ef4444', fontSize:14, fontWeight:600, marginBottom:8 }}>Merge falhou</div>
          <button onClick={() => { setMergeStatus(null); setMergeError(null) }}
            style={{ background:'rgba(255,255,255,.06)', color:'#fff', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'8px 20px', fontSize:13, cursor:'pointer' }}>
            🔄 Tentar novamente
          </button>
        </div>
      )}
    </div>
  )
}

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
      {concept.color_palette && (
        <div>
          <div style={{ fontSize:11, color:'#f97316', fontWeight:600, letterSpacing:1, marginBottom:8 }}>🎨 COLOR PALETTE</div>
          <div style={{ display:'flex', gap:6 }}>
            {concept.color_palette.map((c,i) => (<div key={i} style={{ flex:1, textAlign:'center' }}><div style={{ width:'100%', height:32, background:c, borderRadius:8, marginBottom:4 }} /><div style={{ fontSize:9, color:'#4b5563' }}>{c}</div></div>))}
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
          <span style={{ fontSize:18 }}>🖼️</span>
          <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>CENAS — IMAGENS ({scenes.length})</span>
        </div>
        {scenes.length > 12 && (
          <button onClick={() => setShowAll(!showAll)} style={{ background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.3)', borderRadius:8, padding:'6px 12px', color:'#f97316', fontSize:12, cursor:'pointer' }}>
            {showAll ? 'Mostrar Menos' : `Ver Todas (${scenes.length})`}
          </button>
        )}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(120px,1fr))', gap:10 }}>
        {displayScenes.map((sc, i) => (<SceneImage key={sc.scene_number} scene={sc} index={i} />))}
      </div>
    </div>
  )
}

export default function Dashboard({ onBack }) {
  const [phase, setPhase]         = useState('upload')
  const [credits, setCredits]     = useState(500)
  const [jobId, setJobId]         = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [fileName, setFileName]   = useState('')
  const [serverReady, setServerReady] = useState(false)
  const [completedClips, setCompletedClips] = useState(null)
  const [lipSyncDone,    setLipSyncDone]    = useState(false)
  const [lipSyncUrl,     setLipSyncUrl]     = useState(null)
  const [cancelled,      setCancelled]      = useState(false)
  const pollRef = useRef()

  // ✅ Auto-recupera job ativo ao recarregar a página (como o FREEBEAT)
  useEffect(() => {
    const wake = async () => {
      try {
        const res = await fetch(`${API_URL}/api/health`)
        if (res.ok) {
          setServerReady(true)
          // Tenta retomar job salvo no localStorage
          const savedId   = localStorage.getItem('clipvox_active_job')
          const savedName = localStorage.getItem('clipvox_active_name')
          if (savedId) {
            try {
              const r = await fetch(`${API_URL}/api/videos/status/${savedId}`)
              if (r.ok) {
                const data = await r.json()
                // Só retoma se ainda estiver em processamento ativo
                const activeStatuses = ['processing', 'pending']
                const activeVideo    = ['processing', 'retrying']
                const isActive = activeStatuses.includes(data.status)
                  || activeVideo.includes(data.videos_status)
                  || data.lipsync_status === 'processing'
                  || data.merge_status === 'processing'
                if (isActive || data.status === 'completed') {
                  console.log('♻️ Retomando job salvo:', savedId)
                  handleResume(savedId, data, savedName)
                } else {
                  localStorage.removeItem('clipvox_active_job')
                  localStorage.removeItem('clipvox_active_name')
                }
              }
            } catch(e) { console.warn('Auto-resume falhou:', e) }
          }
          return
        }
      } catch(e) {}
      setTimeout(wake, 5000)
    }
    wake()
  }, [])

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  // ✅ Recupera estado dos clipes e lipsync do Supabase ao carregar jobStatus
  useEffect(() => {
    if (!jobStatus) return
    // Clipes prontos
    if (jobStatus.videos_status === 'completed' && jobStatus.video_clips) {
      setCompletedClips(jobStatus.video_clips)
    }
    // Lip sync já concluído
    if (jobStatus.lipsync_status === 'completed') {
      setLipSyncDone(true)
      setLipSyncUrl(jobStatus.lipsync_url || null)
    }
  }, [jobStatus])

  // ✅ Retomar job existente pelo ID
  const handleResume = (id, data, savedName) => {
    setJobId(id)
    setJobStatus(data)
    const name = savedName || data.file_name || data.audio_filename || `job-${id.slice(0,8)}`
    setFileName(name)
    setPhase('processing')
    // ✅ Persiste no localStorage para sobreviver a reloads
    localStorage.setItem('clipvox_active_job', id)
    localStorage.setItem('clipvox_active_name', name)

    // Inicia polling
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/videos/status/${id}`)
        if (!res.ok) return
        const status = await res.json()
        setJobStatus(status)
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollRef.current)
        }
      } catch(e) { console.warn('Polling:', e) }
    }, 3000)
  }

  const startGeneration = async ({ file, desc, style, duration, aspectRatio, resolution, refImages }) => {
    try {
      setFileName(file.name); setPhase('processing'); setCredits(c => c - 100)
      setCompletedClips(null); setLipSyncDone(false); setLipSyncUrl(null)
      const formData = new FormData()
      formData.append('audio', file)
      formData.append('description', desc)
      formData.append('style', style)
      formData.append('duration', String(duration))
      formData.append('aspect_ratio', aspectRatio)
      formData.append('resolution', resolution)
      ;(refImages || []).slice(0,3).forEach((img, i) => {
        if (img) formData.append(i === 0 ? 'ref_image' : `ref_image_${i+1}`, img)
      })

      const controller = new AbortController()
      const tid = setTimeout(() => controller.abort(), 90000)
      let response
      try {
        response = await fetch(`${API_URL}/api/videos/generate`, { method:'POST', body:formData, signal:controller.signal })
        clearTimeout(tid)
      } catch(fetchErr) {
        clearTimeout(tid)
        alert(fetchErr.name === 'AbortError' ? 'Servidor demorando — aguarde 30s e tente novamente.' : 'Não foi possível conectar ao servidor.')
        setPhase('upload'); return
      }

      if (!response.ok) {
        alert(response.status === 504 ? 'Servidor em cold start. Aguarde 30s e tente.' : `Erro ${response.status}. Tente novamente.`)
        setPhase('upload'); return
      }

      const data = await response.json()
      if (!data.job_id) { alert('Resposta inesperada. Tente novamente.'); setPhase('upload'); return }

      setJobId(data.job_id)
      // ✅ Salva no localStorage para recuperar após reload
      localStorage.setItem('clipvox_active_job', data.job_id)
      localStorage.setItem('clipvox_active_name', file.name)
      pollRef.current = setInterval(async () => {
        try {
          const res    = await fetch(`${API_URL}/api/videos/status/${data.job_id}`)
          if (!res.ok) return
          const status = await res.json()
          setJobStatus(status)
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollRef.current)
            if (status.status === 'failed') alert(`Geração falhou: ${status.error_message || 'Erro desconhecido'}`)
          }
        } catch(e) { console.warn('Polling:', e) }
      }, 2000)

    } catch(error) {
      console.error(error)
      alert('Erro inesperado. Tente novamente.')
      setPhase('upload')
    }
  }

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    localStorage.removeItem('clipvox_active_job')
    localStorage.removeItem('clipvox_active_name')
    setPhase('upload'); setJobId(null); setJobStatus(null); setFileName('')
    setCompletedClips(null); setLipSyncDone(false); setLipSyncUrl(null); setCancelled(false)
  }

  const handleCancel = async () => {
    if (!jobId || cancelled) return
    try {
      await fetch(`${API_URL}/api/videos/cancel/${jobId}`, { method: 'POST' })
      setCancelled(true)
      if (pollRef.current) clearInterval(pollRef.current)
    } catch(e) { console.warn('Cancel error:', e) }
  }

  const handleVideosCompleted = (clips) => {
    if (clips && clips.some(c => c.success)) setCompletedClips(clips)
  }

  const handleLipSyncCompleted = (url) => {
    setLipSyncDone(true)
    setLipSyncUrl(url || null)
  }

  // ✅ Lip sync estava rodando quando o servidor reiniciou?
  const lipSyncWasStuck = jobStatus?.lipsync_status === 'processing' && !lipSyncDone

  if (phase === 'upload') {
    return (
      <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
        <style>{CSS}</style>
        <Navbar onBack={onBack} credits={credits} />
        {!serverReady && (
          <div style={{ background:'rgba(249,115,22,.08)', borderBottom:'1px solid rgba(249,115,22,.2)', padding:'10px 24px', textAlign:'center', display:'flex', alignItems:'center', justifyContent:'center', gap:8 }}>
            <div style={{ width:12, height:12, border:'2px solid rgba(249,115,22,.3)', borderTop:'2px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
            <span style={{ color:'#f97316', fontSize:12 }}>Conectando ao servidor, aguarde alguns segundos...</span>
          </div>
        )}
        <UploadZone onStart={startGeneration} />
        <ResumeJobBox onResume={handleResume} />
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
              <div key={tab} style={{ padding:'7px 16px', borderRadius:8, fontSize:13, fontWeight:500, cursor:'pointer', background: i===1 ? 'rgba(249,115,22,.1)' : 'rgba(255,255,255,.04)', border: i===1 ? '1px solid rgba(249,115,22,.25)' : '1px solid rgba(255,255,255,.06)', color: i===1 ? '#f97316' : '#6b7280' }}>{tab}</div>
            ))}
          </div>

          {!jobStatus && (
            <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:'56px 24px', textAlign:'center' }}>
              {!cancelled ? (
                <>
                  <div style={{ width:38, height:38, margin:'0 auto 14px', border:'3px solid rgba(255,255,255,.1)', borderTop:'3px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
                  <p style={{ color:'#6b7280', fontSize:14, marginBottom:16 }}>Processando sua música com IA...</p>
                  <button onClick={handleCancel} style={{ background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar geração</button>
                </>
              ) : (
                <><div style={{ fontSize:32, marginBottom:10 }}>🛑</div><p style={{ color:'#ef4444', fontSize:14, marginBottom:12 }}>Geração cancelada</p><button onClick={reset} style={{ background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'8px 20px', color:'#fff', fontSize:13, cursor:'pointer' }}>🔄 Novo Videoclipe</button></>
              )}
            </div>
          )}

          {jobStatus?.creative_concept && <CreativeConceptCard concept={jobStatus.creative_concept} />}
          {jobStatus?.scenes && <div style={{ marginTop:16 }}><ScenesGrid scenes={jobStatus.scenes} /></div>}

          {jobStatus?.status === 'completed' && jobId && (
            <>
              <VideoClipsPanel
                jobId={jobId}
                jobStatus={jobStatus}
                onVideosCompleted={handleVideosCompleted}
                onCancel={handleCancel}
              />

              {/* PASSO 2: Lip Sync — aparece quando clipes prontos OU quando estava rodando (stuck) */}
              {(completedClips?.some(c => c.success) || lipSyncWasStuck) && !lipSyncDone && (
                <LipSyncPanel
                  jobId={jobId}
                  videoClips={completedClips}
                  onLipSyncCompleted={handleLipSyncCompleted}
                  initialLipSyncStatus={jobStatus?.lipsync_status}
                  onCancel={handleCancel}
                />
              )}

              {/* PASSO 3: Merge Final */}
              {completedClips?.some(c => c.success) && lipSyncDone && (
                <MergePanel
                  jobId={jobId}
                  videoClips={completedClips}
                  lipSyncUrl={lipSyncUrl}
                />
              )}
            </>
          )}

          {jobStatus?.status === 'failed' && (
            <div style={{ marginTop:16, background:'rgba(239,68,68,.05)', border:'1px solid rgba(239,68,68,.2)', borderRadius:16, padding:'32px 24px', textAlign:'center', animation:'fadeUp .5s ease' }}>
              <div style={{ fontSize:36, marginBottom:12 }}>❌</div>
              <h3 style={{ color:'#ef4444', fontSize:16, fontWeight:600, marginBottom:8 }}>Erro na geração</h3>
              <p style={{ color:'#6b7280', fontSize:13, marginBottom:20 }}>{jobStatus.error_message || 'Erro desconhecido'}</p>
              <button onClick={reset} style={{ background:'rgba(255,255,255,.06)', color:'#fff', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'10px 24px', fontSize:14, cursor:'pointer' }}>🔄 Tentar Novamente</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
