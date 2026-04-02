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

// ✅ Extrai o prompt de uma cena ou clipe tentando vários campos possíveis
function resolvePrompt(item) {
  return item?.prompt
      || item?.prompt_used
      || item?.image_prompt
      || item?.visual_description
      || item?.scene_description
      || item?.scene_prompt
      || item?.description
      || ''
}

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
    const id = jobId.trim(); if (!id) return
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/api/videos/status/${id}`)
      if (!res.ok) throw new Error('Job não encontrado')
      onResume(id, await res.json())
    } catch(e) { setError(e.message || 'Erro ao buscar job') }
    finally { setLoading(false) }
  }
  return (
    <div style={{ maxWidth:780, margin:'0 auto', padding:'0 24px 40px' }}>
      <div style={{ background:'rgba(16,16,24,.7)', border:'1px solid rgba(255,255,255,.07)', borderRadius:14, padding:'18px 20px' }}>
        <div style={{ color:'#6b7280', fontSize:12, fontWeight:600, letterSpacing:.5, marginBottom:10 }}>🔁 RETOMAR JOB EXISTENTE</div>
        <div style={{ display:'flex', gap:8 }}>
          <input value={jobId} onChange={e => setJobId(e.target.value)} placeholder="Cole o Job ID aqui"
            style={{ flex:1, padding:'10px 14px', borderRadius:10, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:12, outline:'none', fontFamily:"'DM Sans',sans-serif" }}
            onKeyDown={e => e.key === 'Enter' && handleResume()} />
          <button onClick={handleResume} disabled={loading || !jobId.trim()}
            style={{ padding:'10px 18px', background: jobId.trim() ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)', border:`1px solid ${jobId.trim() ? 'rgba(249,115,22,.4)' : 'rgba(255,255,255,.08)'}`, borderRadius:10, color: jobId.trim() ? '#f97316' : '#4b5563', fontSize:13, fontWeight:600, cursor: jobId.trim() ? 'pointer' : 'not-allowed', whiteSpace:'nowrap' }}>
            {loading ? '⏳' : '▶ Retomar'}
          </button>
        </div>
        {error && <div style={{ color:'#ef4444', fontSize:11, marginTop:8 }}>❌ {error}</div>}
      </div>
    </div>
  )
}

function HistoryPanel({ onResume }) {
  const [history, setHistory] = useState([])
  const [open, setOpen] = useState(false)
  useEffect(() => {
    try { setHistory(JSON.parse(localStorage.getItem('clipvox_history') || '[]')) } catch(e) {}
  }, [open])
  if (history.length === 0) return null
  return (
    <div style={{ maxWidth:780, margin:'0 auto', padding:'0 24px 32px' }}>
      <div style={{ background:'rgba(16,16,24,.7)', border:'1px solid rgba(255,255,255,.07)', borderRadius:14, overflow:'hidden' }}>
        <div onClick={() => setOpen(o => !o)}
          style={{ padding:'14px 18px', display:'flex', alignItems:'center', justifyContent:'space-between', cursor:'pointer' }}
          onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,.03)'}
          onMouseLeave={e => e.currentTarget.style.background='transparent'}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ fontSize:14 }}>🕓</span>
            <span style={{ color:'#9ca3af', fontSize:12, fontWeight:600, letterSpacing:.5 }}>HISTÓRICO</span>
            <span style={{ background:'rgba(249,115,22,.15)', color:'#f97316', fontSize:10, fontWeight:700, borderRadius:6, padding:'2px 7px' }}>{history.length}</span>
          </div>
          <span style={{ color:'#6b7280', fontSize:12 }}>{open ? '▲' : '▼'}</span>
        </div>
        {open && (
          <div style={{ borderTop:'1px solid rgba(255,255,255,.06)' }}>
            {history.map((item, i) => (
              <div key={item.id} onClick={() => onResume(item.id, null, item.name)}
                style={{ padding:'11px 18px', display:'flex', alignItems:'center', gap:12, cursor:'pointer', borderBottom: i < history.length-1 ? '1px solid rgba(255,255,255,.04)' : 'none' }}
                onMouseEnter={e => e.currentTarget.style.background='rgba(249,115,22,.05)'}
                onMouseLeave={e => e.currentTarget.style.background='transparent'}>
                <span style={{ fontSize:16 }}>🎵</span>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ color:'#fff', fontSize:12, fontWeight:500, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{item.name}</div>
                  <div style={{ color:'#4b5563', fontSize:10, marginTop:2 }}>{item.date} · {item.id.slice(0,8)}</div>
                </div>
                <span style={{ color:'#f97316', fontSize:11, whiteSpace:'nowrap' }}>▶ Retomar</span>
              </div>
            ))}
          </div>
        )}
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
  const [refImages, setRefImages] = useState([])
  const [refPreviews, setRefPreviews] = useState([])
  const fileRef = useRef()
  const imageRefs = [useRef(), useRef(), useRef()]

  const styles = [
    { id:'realistic', label:'Fotorrealista', emoji:'📷' }, { id:'cinematic', label:'Cinemático', emoji:'🎬' },
    { id:'animated', label:'Animado 3D', emoji:'🎨' }, { id:'retro', label:'Retro 80s', emoji:'📺' },
    { id:'anime', label:'Anime', emoji:'🇯🇵' }, { id:'cyberpunk', label:'Cyberpunk', emoji:'🌃' },
    { id:'fantasy', label:'Fantasia', emoji:'🧙' }, { id:'minimalist', label:'Minimalista', emoji:'⬜' },
    { id:'vintage', label:'Vintage', emoji:'📽️' }, { id:'oil_painting', label:'Pintura Óleo', emoji:'🖼️' }
  ]
  const durations = [
    { value:'10', label:'10s' }, { value:'15', label:'15s' }, { value:'30', label:'30s' },
    { value:'60', label:'1min' }, { value:'120', label:'2min' },
    { value:'full', label:'Completo' }, { value:'custom', label:'Personalizado' }
  ]
  const aspectRatios = [
    { value:'16:9', label:'Horizontal', desc:'1920×1080' }, { value:'9:16', label:'Vertical', desc:'1080×1920' },
    { value:'1:1', label:'Quadrado', desc:'1080×1080' }, { value:'4:3', label:'Clássico', desc:'1440×1080' }
  ]
  const resolutions = [{ value:'720p', label:'720p', desc:'Rápido' }, { value:'1080p', label:'1080p', desc:'Premium' }]

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
        style={{ border: dragging ? '2px dashed #f97316' : file ? '2px dashed rgba(249,115,22,.5)' : '2px dashed rgba(255,255,255,.12)', borderRadius:18, padding:'44px 20px', textAlign:'center', cursor:'pointer', background: dragging ? 'rgba(249,115,22,.05)' : 'rgba(16,16,24,.6)', transition:'all .3s', marginBottom:22 }}>
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
          <div key={idx} onClick={() => imageRefs[idx].current.click()}
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
      <label style={{ display:'block', color:'#9ca3af', fontSize:12, fontWeight:500, letterSpacing:.5, marginBottom:8 }}>📝 DESCRIÇÃO DO VIDEOCLIPE</label>
      <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3}
        placeholder="Ex: Videoclipe sobre o universo do forró nordestino, com cenas da caatinga e festa..."
        style={{ width:'100%', padding:'13px 16px', borderRadius:12, background:'rgba(16,16,24,.8)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:13, lineHeight:1.6, resize:'vertical', outline:'none', fontFamily:"'DM Sans',sans-serif", marginBottom:24 }}
        onFocus={e => e.target.style.borderColor='rgba(249,115,22,.4)'}
        onBlur={e => e.target.style.borderColor='rgba(255,255,255,.1)'} />
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
  const stepDesc = {
    plan:      'Criando o plano narrativo e estrutura do videoclipe...',
    analyzing: 'Analisando BPM, ritmo e estrutura musical do áudio...',
    creative:  'Gerando conceito criativo, paleta de cores e direção visual...',
    scenes:    'Gerando imagens de cada cena com IA (Nano Banana)...',
    segments:  'Convertendo imagens em clipes de vídeo com Kling AI...',
    merge:     'Unindo todos os clipes e adicionando o áudio final...',
  }
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
            <div key={step}>
              <div style={{ display:'flex', alignItems:'center', gap:12, padding:'9px 0', borderBottom: (!active && i < steps.length-1) ? '1px solid rgba(255,255,255,.045)' : 'none' }}>
                <div style={{ width:26, height:26, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', background: done ? 'rgba(34,197,94,.15)' : active ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)', border: done ? '1px solid rgba(34,197,94,.4)' : active ? '1px solid rgba(249,115,22,.4)' : '1px solid rgba(255,255,255,.1)', fontSize:11, fontWeight:700, color: done ? '#22c55e' : active ? '#f97316' : '#4b5563' }}>
                  {done ? '✓' : active ? <div style={{ width:8,height:8,border:'2px solid rgba(249,115,22,.4)',borderTop:'2px solid #f97316',borderRadius:'50%',animation:'spin .8s linear infinite' }} /> : i+1}
                </div>
                <span style={{ flex:1, fontSize:13, fontWeight: active ? 600 : 400, color: done ? '#6b7280' : active ? '#fff' : '#4b5563' }}>{stepLabels[step]}</span>
                {done && <span style={{ color:'#22c55e', fontSize:15 }}>✓</span>}
              </div>
              {/* Descrição do step ativo logo abaixo */}
              {active && (
                <div style={{ margin:'2px 0 10px 38px', padding:'8px 12px', background:'rgba(249,115,22,.06)', border:'1px solid rgba(249,115,22,.15)', borderRadius:8, borderBottom:'1px solid rgba(255,255,255,.045)', animation:'fadeUp .3s ease' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
                    <div style={{ width:6,height:6,borderRadius:'50%',background:'#f97316',animation:'pulse 1.4s ease infinite' }} />
                    <span style={{ color:'#f97316', fontSize:9, fontWeight:700, letterSpacing:.5 }}>EM ANDAMENTO</span>
                  </div>
                  <p style={{ color:'#9ca3af', fontSize:11, lineHeight:1.6 }}>{stepDesc[step]}</p>
                </div>
              )}
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

// ══════════════════════════════════════════════════════
// 🎬 MODAL DE EDIÇÃO DE CENA / VÍDEO
// ✅ FIX A: prompt resolvido por múltiplos campos possíveis
// ══════════════════════════════════════════════════════
function SceneEditModal({ item, type, jobId, onClose, onRegenerated }) {
  // ✅ resolvePrompt tenta vários campos — item já vem enriquecido com scenePrompt
  const [prompt,  setPrompt]  = useState(resolvePrompt(item))
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef()

  const handleRegen = async () => {
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('prompt', prompt)
      const endpoint = type === 'scene'
        ? `${API_URL}/api/videos/regen-scene/${jobId}/${item.scene_number}`
        : `${API_URL}/api/videos/regen-video/${jobId}/${item.scene_number}`
      const res = await fetch(endpoint, { method: 'POST', body: formData })
      if (!res.ok) { const e = await res.json().catch(() => {}); throw new Error(e?.detail || `Erro ${res.status}`) }
      setSuccess(true)
      setTimeout(() => { onRegenerated(); onClose() }, 1500)
    } catch(e) {
      alert('Erro: ' + e.message)
    } finally { setLoading(false) }
  }

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,.85)', zIndex:200, display:'flex', alignItems:'center', justifyContent:'center', padding:20 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background:'#111118', border:'1px solid rgba(255,255,255,.1)', borderRadius:18, width:'100%', maxWidth:820, maxHeight:'90vh', overflow:'auto', padding:28, position:'relative', animation:'fadeUp .3s ease' }}>
        <button onClick={onClose} style={{ position:'absolute', top:14, right:16, background:'rgba(255,255,255,.07)', border:'none', borderRadius:8, color:'#9ca3af', fontSize:16, cursor:'pointer', padding:'4px 10px' }}>✕</button>
        <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:20 }}>
          <span style={{ fontSize:20 }}>{type === 'scene' ? '🖼️' : '🎬'}</span>
          <div>
            <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:16, letterSpacing:2, color:'#fff' }}>
              {type === 'scene' ? 'EDITAR CENA' : 'EDITAR VÍDEO'} #{item.scene_number}
            </div>
            <div style={{ color:'#6b7280', fontSize:11 }}>Edite o prompt e regenere apenas esta cena</div>
          </div>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:20 }}>
          <div>
            <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, letterSpacing:.5, marginBottom:8 }}>
              {type === 'scene' ? '🖼️ IMAGEM ATUAL' : '🎬 VÍDEO ATUAL'}
            </div>
            <div style={{ borderRadius:12, overflow:'hidden', background:'#0a0a0e', position:'relative' }}>
              {type === 'scene' ? (
                <img src={item.image_url} alt={`Cena ${item.scene_number}`}
                  style={{ width:'100%', display:'block', maxHeight:220, objectFit:'cover' }} />
              ) : (
                <div style={{ position:'relative', cursor:'pointer' }}
                  onClick={() => { if(videoRef.current) { if(playing){ videoRef.current.pause(); setPlaying(false) } else { videoRef.current.play(); setPlaying(true) } } }}>
                  <video ref={videoRef} src={item.video_url} loop playsInline
                    style={{ width:'100%', display:'block', maxHeight:220, objectFit:'cover' }}
                    onEnded={() => setPlaying(false)} />
                  {!playing && (
                    <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(0,0,0,.4)' }}>
                      <div style={{ width:40, height:40, borderRadius:'50%', background:'rgba(249,115,22,.9)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:14 }}>▶</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div>
            <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, letterSpacing:.5, marginBottom:8 }}>✏️ PROMPT</div>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={9}
              placeholder="Digite o prompt para gerar esta cena..."
              style={{ width:'100%', padding:'12px', borderRadius:12, background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)', color:'#fff', fontSize:12, lineHeight:1.6, resize:'vertical', outline:'none', fontFamily:"'DM Sans',sans-serif" }}
              onFocus={e => e.target.style.borderColor='rgba(249,115,22,.4)'}
              onBlur={e => e.target.style.borderColor='rgba(255,255,255,.1)'} />
            <div style={{ color:'#4b5563', fontSize:10, marginTop:4 }}>
              {prompt ? 'Edite o prompt acima para alterar o resultado' : '⚠️ Prompt não disponível — escreva um novo para regenerar'}
            </div>
          </div>
        </div>
        {success ? (
          <div style={{ textAlign:'center', padding:'12px', background:'rgba(34,197,94,.1)', borderRadius:10, color:'#22c55e', fontSize:13, fontWeight:600 }}>
            ✅ Regeneração iniciada! A cena será atualizada em breve.
          </div>
        ) : (
          <div style={{ display:'flex', gap:10 }}>
            <button onClick={handleRegen} disabled={loading || !prompt.trim()}
              style={{ flex:1, padding:'13px', background: prompt.trim() ? 'linear-gradient(135deg,#f97316,#ea580c)' : 'rgba(60,60,70,.5)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor: prompt.trim() ? 'pointer' : 'not-allowed', boxShadow: prompt.trim() ? '0 4px 18px rgba(249,115,22,.3)' : 'none', transition:'all .25s' }}>
              {loading ? '⏳ Regenerando...' : `🔄 Regenerar ${type === 'scene' ? 'Imagem' : 'Vídeo'}`}
            </button>
            <button onClick={onClose}
              style={{ padding:'13px 20px', background:'rgba(255,255,255,.06)', color:'#9ca3af', border:'1px solid rgba(255,255,255,.1)', borderRadius:12, fontSize:13, cursor:'pointer' }}>
              Cancelar
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function SceneImage({ scene, index, onEdit }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError]   = useState(false)
  const isRegen = scene?.regenerating
  return (
    <div onClick={() => onEdit && onEdit(scene)} style={{ background:'rgba(255,255,255,.03)', border:`1px solid ${isRegen ? 'rgba(249,115,22,.5)' : 'rgba(255,255,255,.06)'}`, borderRadius:11, overflow:'hidden', cursor:'pointer', transition:'all .25s', animation:`fadeUp .4s ease ${index*0.04}s both`, position:'relative' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(249,115,22,.3)'; e.currentTarget.style.transform='translateY(-2px)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = isRegen ? 'rgba(249,115,22,.5)' : 'rgba(255,255,255,.06)'; e.currentTarget.style.transform='translateY(0)' }}>
      <div style={{ height:82, position:'relative', background:'#0a0a0e' }}>
        {!loaded && !error && <div className="skeleton" style={{ width:'100%', height:'100%', position:'absolute', top:0, left:0 }} />}
        {scene.image_url && !error ? (
          <img src={scene.image_url} alt={`Scene ${scene.scene_number}`} onLoad={() => setLoaded(true)} onError={() => setError(true)}
            style={{ width:'100%', height:'100%', objectFit:'cover', opacity: loaded ? 1 : 0, transition:'opacity .3s' }} />
        ) : (
          <div style={{ width:'100%', height:'100%', background:`linear-gradient(135deg, rgba(${80+index*10},${40+index*5},${20+index*8},1), rgba(10,10,14,1))`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:24 }}>🎬</div>
        )}
        <div style={{ position:'absolute', bottom:5, left:5, background:'rgba(0,0,0,.7)', borderRadius:4, padding:'2px 5px', fontSize:9, color:'#fff' }}>Scene {scene.scene_number}</div>
        <div style={{ position:'absolute', top:4, right:4, background:'rgba(0,0,0,.6)', borderRadius:4, padding:'2px 6px', fontSize:9, color:'#f97316' }}>✏️</div>
        {isRegen && <div style={{ position:'absolute', inset:0, background:'rgba(249,115,22,.15)', display:'flex', alignItems:'center', justifyContent:'center' }}><div style={{ width:24, height:24, border:'2px solid rgba(249,115,22,.3)', borderTop:'2px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} /></div>}
      </div>
      <div style={{ padding:'8px 9px' }}>
        <div style={{ fontSize:10, color:'#fff', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{scene.camera_movement}</div>
        <div style={{ fontSize:9, color:'#4b5563', marginTop:1 }}>{scene.duration_seconds}s · {scene.mood}</div>
      </div>
    </div>
  )
}

// ✅ FIX B: onRetryLipSync prop — botão de refazer sync por cena individual
function VideoClipCard({ clip, index, onEdit, onRetryLipSync }) {
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

  const lipError     = clip.lipsync_error
  const lipRegen     = clip.lipsync_regenerating
  const lipErrorType = clip.lipsync_error_type
  const lipErrorIcon = lipErrorType === 'no_face' ? '🚫' : lipErrorType === 'proxy' ? '🔄' : lipErrorType === 'busy' ? '⏱️' : '⚠️'
  const lipErrorColor = lipErrorType === 'no_face' ? '#f97316' : '#facc15'

  return (
    <div style={{ background:'rgba(16,16,24,.9)', border:`1px solid ${lipError ? 'rgba(250,204,21,.2)' : 'rgba(255,255,255,.08)'}`, borderRadius:12, overflow:'hidden', animation:`fadeUp .4s ease ${index*0.06}s both`, transition:'all .25s' }}
      onMouseEnter={e => e.currentTarget.style.borderColor = lipError ? 'rgba(250,204,21,.4)' : 'rgba(249,115,22,.35)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = lipError ? 'rgba(250,204,21,.2)' : 'rgba(255,255,255,.08)'}>
      <div style={{ position:'relative', background:'#000', cursor:'pointer' }} onClick={togglePlay}>
        <video ref={videoRef} src={clip.video_url} loop muted playsInline
          style={{ width:'100%', display:'block', maxHeight:140, objectFit:'cover' }}
          onEnded={() => setPlaying(false)} />
        <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', background: playing ? 'transparent' : 'rgba(0,0,0,.4)', transition:'background .2s' }}>
          {!playing && (<div style={{ width:38, height:38, borderRadius:'50%', background:'rgba(249,115,22,.9)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:14 }}>▶</div>)}
        </div>
        <div style={{ position:'absolute', top:6, left:6, background:'rgba(0,0,0,.75)', borderRadius:4, padding:'2px 7px', fontSize:9, color:'#fff', fontWeight:600 }}>CENA {clip.scene_number}</div>
        <div style={{ position:'absolute', top:6, right:6, background:'rgba(249,115,22,.8)', borderRadius:4, padding:'2px 7px', fontSize:9, color:'#fff', fontWeight:600 }}>{clip.duration}s</div>
        {/* Badge de erro de lip sync */}
        {lipError && !lipRegen && (
          <div style={{ position:'absolute', bottom:0, left:0, right:0, background:'rgba(0,0,0,.82)', padding:'5px 8px', display:'flex', alignItems:'center', gap:5 }}>
            <span style={{ fontSize:10 }}>{lipErrorIcon}</span>
            <span style={{ color: lipErrorColor, fontSize:9, fontWeight:600, lineHeight:1.3, flex:1 }}>{lipError}</span>
          </div>
        )}
        {/* Spinner quando está refazendo lip sync */}
        {lipRegen && (
          <div style={{ position:'absolute', inset:0, background:'rgba(139,92,246,.15)', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:8 }}>
            <div style={{ width:28, height:28, border:'3px solid rgba(139,92,246,.3)', borderTop:'3px solid #a78bfa', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
            <div style={{ color:'#a78bfa', fontSize:10, fontWeight:600 }}>Sincronizando...</div>
          </div>
        )}
      </div>
      <div style={{ padding:'10px 12px', display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:4 }}>
        <div style={{ color: lipError ? lipErrorColor : '#9ca3af', fontSize:10 }}>
          Kling AI · {clip.mode === 'pro' ? '⭐ Pro' : 'Standard'}
          {lipError ? ' · ⚠️ sem sync' : ' · 🎤 sincronizado'}
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          {/* ✅ FIX B: Botão refazer lip sync — só aparece se há erro E onRetryLipSync foi passado */}
          {lipError && !lipRegen && onRetryLipSync && (
            <button onClick={e => { e.stopPropagation(); onRetryLipSync(clip.scene_number) }}
              style={{ background:'rgba(139,92,246,.15)', border:'1px solid rgba(139,92,246,.4)', borderRadius:6, padding:'3px 8px', color:'#a78bfa', fontSize:10, cursor:'pointer', fontWeight:600 }}>
              🔄 Refazer Sync
            </button>
          )}
          {onEdit && <button onClick={e => { e.stopPropagation(); onEdit(clip) }}
            style={{ background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.3)', borderRadius:6, padding:'3px 8px', color:'#f97316', fontSize:10, cursor:'pointer' }}>
            ✏️ Editar
          </button>}
          <a href={clip.video_url} download={`cena_${clip.scene_number}.mp4`} target="_blank" rel="noreferrer"
            style={{ color:'#f97316', fontSize:10, textDecoration:'none' }}
            onClick={e => e.stopPropagation()}>⬇ Baixar</a>
        </div>
      </div>
    </div>
  )
}

function VideoClipsPanel({ jobId, jobStatus, onVideosCompleted, onCancel, onEditClip }) {
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
            clearInterval(pollRef.current); setGenerating(false)
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
      if (err.name === 'AbortError') return
      setError(err.message || 'Erro ao iniciar geração de vídeos')
      setGenerating(false); setVideosStatus(null)
    }
  }

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

  const scenes      = jobStatus?.scenes || []
  const totalClips  = scenes.filter(s => s.success).length
  const successClips = videoClips?.filter(c => c.success) || []
  const failedClips  = videoClips?.filter(c => !c.success || !c.video_url) || []
  const estimatedCost = (totalClips * (klingMode === 'std' ? 0.125 : 0.25)).toFixed(2)

  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:24, marginTop:16, animation:'fadeUp .5s ease' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ fontSize:20 }}>🎬</span>
          <div>
            <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:15, letterSpacing:2, color:'#fff' }}>SEGMENTOS DE VÍDEO</div>
            <div style={{ color:'#6b7280', fontSize:11, marginTop:1 }}>Kling AI 2.1 (PiAPI) · Image-to-Video</div>
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
            {[{ value:'std', label:'Standard', price:'~$0.125/clipe', desc:'Bom para testes' },
              { value:'pro', label:'Professional', price:'~$0.25/clipe', desc:'Qualidade cinematográfica' }].map(m => (
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
              <div style={{ color:'#6b7280', fontSize:11, marginTop:2 }}>{totalClips} clipes × {klingMode === 'std' ? '$0.125' : '$0.25'} = <span style={{ color:'#fff', fontWeight:600 }}>${estimatedCost}</span></div>
            </div>
            <div style={{ color:'#4b5563', fontSize:11 }}>{totalClips} imagens prontas</div>
          </div>
          {error && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {error}</div>)}
          <button onClick={handleGenerate}
            style={{ width:'100%', padding:'13px', background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(249,115,22,.3)' }}>
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
                <div style={{ color:'#6b7280', fontSize:11 }}>Cenas: {failedClips.map(c => c.scene_number).join(', ')}</div>
              </div>
              <button onClick={handleRetry}
                style={{ padding:'8px 18px', background:'linear-gradient(135deg,#f97316,#ea580c)', color:'#fff', border:'none', borderRadius:10, fontSize:12, fontWeight:600, cursor:'pointer' }}>
                🔄 Regenerar {failedClips.length} cena(s)
              </button>
            </div>
          )}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px,1fr))', gap:12, marginTop:4 }}>
            {videoClips.map((clip, i) => (<VideoClipCard key={clip.scene_number || i} clip={clip} index={i} onEdit={onEditClip} />))}
          </div>
        </>
      )}

      {videosStatus === 'retrying' && (
        <div style={{ textAlign:'center', padding:'24px 0' }}>
          <div style={{ width:44, height:44, margin:'0 auto 16px', border:'3px solid rgba(234,179,8,.2)', borderTop:'3px solid #eab308', borderRadius:'50%', animation:'spin .9s linear infinite' }} />
          <div style={{ color:'#fff', fontSize:14, fontWeight:600, marginBottom:6 }}>Regenerando cenas com falha...</div>
          <div style={{ color:'#6b7280', fontSize:12 }}>Apenas as cenas que falharam</div>
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
// ✅ FIX B: mostra lipsync_clips com botão individual de retry por cena
// ✅ FIX C: polling de regen individual via lipsync_regenerating
// ══════════════════════════════════════════════════════════════════════════════
function LipSyncPanel({ jobId, videoClips, onLipSyncCompleted, initialLipSyncStatus, onCancel, onRetrySyncClip, lipSyncClips, initialLipUrl }) {
  const isStuck = initialLipSyncStatus === 'processing'
  // ✅ FIX C: inicializa como 'completed' quando lip sync já foi concluído (ex: retomando job)
  const [status,    setStatus]    = useState(
    isStuck ? 'stuck' : initialLipSyncStatus === 'completed' ? 'completed' : null
  )
  const [lipUrl,    setLipUrl]    = useState(initialLipUrl || null)
  const [error,     setError]     = useState(null)
  const [model,     setModel]     = useState('kling')
  const [skipped,   setSkipped]   = useState(false)
  const [audioFile, setAudioFile] = useState(null)
  const pollRef  = useRef()
  const audioRef = useRef()

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  const handleStart = async () => {
    if (status === 'stuck' && !audioFile) {
      setError('O servidor foi reiniciado e o áudio foi perdido. Selecione o arquivo de áudio para refazer.')
      return
    }
    setStatus('processing'); setError(null)
    try {
      const formData = new FormData()
      formData.append('model', model)
      if (audioFile) formData.append('audio', audioFile)
      const res = await fetch(`${API_URL}/api/videos/lipsync/${jobId}`, { method:'POST', body:formData })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Erro ${res.status}`) }
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const s = await r.json()
          if (s.lipsync_status === 'completed' && s.lipsync_clips?.some(c => c.success)) {
            clearInterval(pollRef.current); setStatus('completed'); setLipUrl(s.lipsync_url)
            if (onLipSyncCompleted) onLipSyncCompleted(s.lipsync_url, s.lipsync_clips)
          } else if (s.lipsync_status === 'failed') {
            clearInterval(pollRef.current); setStatus('failed'); setError(s.lipsync_error || 'Lip sync falhou')
          }
        } catch(e) { console.warn('Polling lipsync:', e) }
      }, 5000)
    } catch(err) {
      setError(err.message || 'Erro ao iniciar lip sync'); setStatus('stuck')
    }
  }

  const handleSkip = () => { setSkipped(true); if (onLipSyncCompleted) onLipSyncCompleted(null, null) }
  if (skipped) return null

  // ✅ Conta cenas com erro de lip sync
  const failedSyncClips = (lipSyncClips || []).filter(c => c.lipsync_error && !c.lipsync_regenerating)
  const syncingClips    = (lipSyncClips || []).filter(c => c.lipsync_regenerating)

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
        {status !== 'stuck' && status !== 'completed' && (
          <div style={{ background:'rgba(139,92,246,.1)', border:'1px solid rgba(139,92,246,.3)', borderRadius:8, padding:'4px 12px', color:'#a78bfa', fontSize:11, fontWeight:600 }}>✨ Novo</div>
        )}
        {status === 'completed' && (
          <div style={{ background:'rgba(34,197,94,.1)', border:'1px solid rgba(34,197,94,.3)', borderRadius:8, padding:'4px 12px', color:'#22c55e', fontSize:11, fontWeight:600 }}>
            ✓ {(lipSyncClips || []).filter(c => !c.lipsync_error).length}/{lipSyncClips?.length || 0} sincronizados
          </div>
        )}
      </div>

      {/* ESTADO TRAVADO */}
      {status === 'stuck' && (
        <div style={{ marginBottom:16 }}>
          <div style={{ background:'rgba(234,179,8,.08)', border:'1px solid rgba(234,179,8,.25)', borderRadius:10, padding:'14px 16px', marginBottom:16 }}>
            <div style={{ color:'#eab308', fontSize:13, fontWeight:600, marginBottom:6 }}>⚠️ Lip sync interrompido</div>
            <div style={{ color:'#9ca3af', fontSize:12, lineHeight:1.7 }}>
              O servidor foi reiniciado e o áudio foi perdido.<br/>
              <strong style={{ color:'#fff' }}>Faça upload da música novamente</strong> para refazer o lip sync.
            </div>
          </div>
          <div onClick={() => audioRef.current.click()}
            style={{ border: audioFile ? '2px dashed rgba(139,92,246,.5)' : '2px dashed rgba(139,92,246,.25)', borderRadius:12, padding:'18px', textAlign:'center', cursor:'pointer', background:'rgba(139,92,246,.04)', marginBottom:14 }}>
            <input ref={audioRef} type="file" accept="audio/*" style={{ display:'none' }}
              onChange={e => { const f = e.target.files[0]; if (f) setAudioFile(f) }} />
            {audioFile
              ? <><div style={{ fontSize:24, marginBottom:6 }}>🎵</div><div style={{ color:'#a78bfa', fontSize:13, fontWeight:600 }}>{audioFile.name}</div></>
              : <><div style={{ fontSize:28, marginBottom:6 }}>📂</div><div style={{ color:'#fff', fontSize:13, fontWeight:600, marginBottom:4 }}>Selecionar arquivo de áudio</div><div style={{ color:'#6b7280', fontSize:11 }}>MP3 · WAV · OGG · M4A</div></>}
          </div>
          {error && <div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:12, color:'#ef4444', fontSize:12 }}>❌ {error}</div>}
          <button onClick={handleStart} disabled={!audioFile}
            style={{ width:'100%', padding:'13px', background: audioFile ? 'linear-gradient(135deg,#7c3aed,#6d28d9)' : 'rgba(60,60,70,.5)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor: audioFile ? 'pointer' : 'not-allowed', marginBottom:10 }}>
            🎤 Refazer Lip Sync com novo áudio
          </button>
          <button onClick={handleSkip}
            style={{ width:'100%', padding:'10px', background:'transparent', color:'#4b5563', border:'1px solid rgba(255,255,255,.07)', borderRadius:10, fontSize:13, cursor:'pointer' }}>
            Pular — ir direto para o Merge
          </button>
        </div>
      )}

      {/* ESTADO INICIAL */}
      {status === null && (
        <>
          <div style={{ background:'rgba(139,92,246,.06)', border:'1px solid rgba(139,92,246,.15)', borderRadius:10, padding:'12px 16px', marginBottom:16 }}>
            <div style={{ color:'#a78bfa', fontSize:12, fontWeight:600, marginBottom:6 }}>🧠 Como funciona:</div>
            <div style={{ color:'#9ca3af', fontSize:12, lineHeight:1.8 }}>
              1️⃣ StemSplit extrai <strong style={{color:'#fff'}}>apenas a voz</strong> da música<br/>
              2️⃣ Kling AI sincroniza a boca do personagem com a voz limpa<br/>
              3️⃣ Resultado: <strong style={{color:'#fff'}}>lábios movendo em perfeita sincronia</strong> com a letra
            </div>
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:16 }}>
            {[{ value:'kling', label:'Kling Standard', desc:'~$0.10/5s', quality:'Bom' },
              { value:'kling-v1-5', label:'Kling v1.5', desc:'~$0.10/5s', quality:'Excelente' }].map(m => (
              <div key={m.value} onClick={() => setModel(m.value)}
                style={{ padding:'12px 14px', borderRadius:12, cursor:'pointer', background: model===m.value ? 'rgba(139,92,246,.1)' : 'rgba(255,255,255,.03)', border: model===m.value ? '1px solid rgba(139,92,246,.4)' : '1px solid rgba(255,255,255,.07)' }}>
                <div style={{ color: model===m.value ? '#a78bfa' : '#fff', fontSize:13, fontWeight:600, marginBottom:2 }}>{m.label}</div>
                <div style={{ color:'#a78bfa', fontSize:11, fontWeight:600, marginBottom:2 }}>{m.desc}</div>
                <div style={{ color:'#6b7280', fontSize:10 }}>Qualidade: {m.quality}</div>
              </div>
            ))}
          </div>
          {error && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {error}</div>)}
          <button onClick={handleStart}
            style={{ width:'100%', padding:'13px', background:'linear-gradient(135deg,#7c3aed,#6d28d9)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(124,58,237,.3)', marginBottom:10 }}>
            🎤 Aplicar Lip Sync na Música
          </button>
          <button onClick={handleSkip}
            style={{ width:'100%', padding:'10px', background:'transparent', color:'#4b5563', border:'1px solid rgba(255,255,255,.07)', borderRadius:10, fontSize:13, cursor:'pointer' }}>
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
          {onCancel && <button onClick={onCancel} style={{ marginTop:16, background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar</button>}
        </div>
      )}

      {/* ✅ FIX B: Estado concluído com grid de lipsync_clips e botão de retry individual */}
      {status === 'completed' && lipSyncClips && lipSyncClips.length > 0 && (
        <>
          {/* Banner de aviso se houver falhas */}
          {failedSyncClips.length > 0 && (
            <div style={{ background:'rgba(250,204,21,.06)', border:'1px solid rgba(250,204,21,.2)', borderRadius:10, padding:'12px 16px', marginBottom:16 }}>
              <div style={{ color:'#facc15', fontSize:12, fontWeight:600, marginBottom:6 }}>
                ⚠️ {failedSyncClips.length} cena{failedSyncClips.length > 1 ? 's' : ''} sem sincronização — cenas: {failedSyncClips.map(c => c.scene_number).join(', ')}
              </div>
              <div style={{ color:'#9ca3af', fontSize:11, marginBottom:8 }}>
                Clique em <strong style={{color:'#a78bfa'}}>🔄 Refazer Sync</strong> no card da cena para reprocessar individualmente.
                Custo: ~${(failedSyncClips.length * 0.10).toFixed(2)} por cena retentada.
              </div>
              {syncingClips.length > 0 && (
                <div style={{ color:'#a78bfa', fontSize:11 }}>
                  ⏳ {syncingClips.length} cena(s) sendo reprocessada(s)...
                </div>
              )}
            </div>
          )}

          {/* Grid de clips com status de lip sync */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px,1fr))', gap:12, marginBottom:16 }}>
            {lipSyncClips.map((clip, i) => (
              <VideoClipCard
                key={clip.scene_number || i}
                clip={clip}
                index={i}
                onRetryLipSync={onRetrySyncClip}
              />
            ))}
          </div>

          {/* Links do vídeo lip sync principal */}
          {lipUrl && (
            <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap', marginTop:8 }}>
              <a href={lipUrl} target="_blank" rel="noreferrer"
                style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'11px 22px', background:'linear-gradient(135deg,#7c3aed,#6d28d9)', color:'#fff', borderRadius:12, fontSize:13, fontWeight:600, textDecoration:'none' }}>
                ▶ Ver Lip Sync
              </a>
              <a href={lipUrl} download={`lipsync_${jobId}.mp4`}
                style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'11px 22px', background:'rgba(255,255,255,.07)', color:'#fff', border:'1px solid rgba(255,255,255,.15)', borderRadius:12, fontSize:13, fontWeight:600, textDecoration:'none' }}>
                ⬇ Baixar
              </a>
            </div>
          )}
          <div style={{ color:'#4b5563', fontSize:11, textAlign:'center', marginTop:12 }}>Agora você pode fazer o Merge com o lip sync aplicado ↓</div>
        </>
      )}

      {/* Fallback quando não há lipSyncClips (lip sync concluído mas clips não carregados) */}
      {status === 'completed' && (!lipSyncClips || lipSyncClips.length === 0) && lipUrl && (
        <div style={{ textAlign:'center', padding:'16px 0' }}>
          <div style={{ fontSize:40, marginBottom:12 }}>🎤✨</div>
          <div style={{ color:'#a78bfa', fontSize:16, fontWeight:700, marginBottom:6 }}>Lip Sync concluído!</div>
          <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap', marginTop:12 }}>
            <a href={lipUrl} target="_blank" rel="noreferrer"
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'linear-gradient(135deg,#7c3aed,#6d28d9)', color:'#fff', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ▶ Ver Lip Sync
            </a>
          </div>
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

// ✅ Força download real via Blob — evita que o browser abra o arquivo inline
async function forceDownload(url, filename) {
  try {
    const res  = await fetch(url)
    const blob = await res.blob()
    const a    = document.createElement('a')
    a.href     = URL.createObjectURL(blob)
    a.download = filename
    document.body.appendChild(a); a.click()
    setTimeout(() => { URL.revokeObjectURL(a.href); document.body.removeChild(a) }, 200)
  } catch(e) {
    // fallback: abre em nova aba se fetch falhar (CORS)
    window.open(url, '_blank')
  }
}

function MergePanel({ jobId, videoClips, lipSyncUrl, initialMergeStatus, initialMergeUrl }) {
  // ✅ FIX: inicializa com o status real do job — evita mostrar botão quando merge já concluído
  const [mergeStatus, setMergeStatus] = useState(initialMergeStatus || null)
  const [mergeUrl,    setMergeUrl]    = useState(initialMergeUrl || null)
  const [mergeError,  setMergeError]  = useState(null)
  const [loading,     setLoading]     = useState(false)
  const pollRef = useRef()
  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  // ✅ FIX: se o job já tinha merge concluído ao montar, atualiza estado
  useEffect(() => {
    if (initialMergeStatus === 'completed' && initialMergeUrl) {
      setMergeStatus('completed'); setMergeUrl(initialMergeUrl)
    }
  }, [initialMergeStatus, initialMergeUrl])

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
      setMergeError(err.message || 'Erro ao iniciar merge'); setLoading(false); setMergeStatus(null)
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
              {lipSyncUrl ? '🎤 Lip sync aplicado' : '🎵 Áudio original adicionado'}<br/>
              📦 Vídeo final exportado em MP4
            </div>
          </div>
          {mergeError && (<div style={{ background:'rgba(239,68,68,.08)', border:'1px solid rgba(239,68,68,.2)', borderRadius:8, padding:'10px 14px', marginBottom:16, color:'#ef4444', fontSize:12 }}>❌ {mergeError}</div>)}
          <button onClick={handleMerge}
            style={{ width:'100%', padding:'14px', background:'linear-gradient(135deg,#22c55e,#16a34a)', color:'#fff', border:'none', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer', boxShadow:'0 4px 18px rgba(34,197,94,.3)' }}>
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
          <div style={{ color:'#9ca3af', fontSize:12, marginBottom:16 }}>Acesse a aba <strong style={{ color:'#fff' }}>Resultado</strong> para assistir e baixar</div>
          <div style={{ display:'flex', gap:10, justifyContent:'center', flexWrap:'wrap' }}>
            <a href={mergeUrl} target="_blank" rel="noreferrer"
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'linear-gradient(135deg,#22c55e,#16a34a)', color:'#fff', borderRadius:12, fontSize:14, fontWeight:600, textDecoration:'none' }}>
              ▶ Assistir Vídeo
            </a>
            {/* ✅ FIX: forceDownload via Blob — evita abrir no browser */}
            <button onClick={() => forceDownload(mergeUrl, `clipvox_${jobId}.mp4`)}
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'12px 24px', background:'rgba(255,255,255,.07)', color:'#fff', border:'1px solid rgba(255,255,255,.15)', borderRadius:12, fontSize:14, fontWeight:600, cursor:'pointer' }}>
              ⬇ Baixar MP4
            </button>
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

function ScenesGrid({ scenes, jobId, onEditScene }) {
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
        {displayScenes.map((sc, i) => (<SceneImage key={sc.scene_number} scene={sc} index={i} onEdit={onEditScene} />))}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════
// 🎛️ EDITOR — Timeline de segmentos + waveform MP3
// ══════════════════════════════════════════════════════
function EditorTimeline({ items, selectedIdx, onSelect, color, fileName }) {
  const [hovered, setHovered] = useState(null)
  return (
    <div style={{ background:'rgba(8,8,12,.9)', borderTop:'1px solid rgba(255,255,255,.06)', padding:'10px 14px 12px' }}>
      {/* Barra de controles */}
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:6, color:'#6b7280', fontSize:11 }}>
        <span style={{ cursor:'pointer' }}>✂️</span>
        <div style={{ flex:1, display:'flex', justifyContent:'center', alignItems:'center', gap:8 }}>
          <span>▶</span>
          <span style={{ color:'#9ca3af' }}>0:00:00</span>
        </div>
        <span style={{ fontSize:10 }}>🔍−</span>
        <input type="range" min={0} max={100} defaultValue={50} style={{ width:70, accentColor:color }} />
        <span style={{ fontSize:10 }}>🔍+</span>
      </div>
      {/* Marcadores de tempo */}
      <div style={{ position:'relative', height:12, marginBottom:2 }}>
        {['s','30s','1m','1:30','2m','2:30','3m'].map((label, i, arr) => (
          <span key={i} style={{ position:'absolute', left:`${(i/(arr.length-1))*100}%`, fontSize:8.5, color:'#374151', transform:'translateX(-50%)' }}>{label}</span>
        ))}
      </div>
      {/* Segmentos clicáveis */}
      <div style={{ height:26, background:'rgba(255,255,255,.03)', borderRadius:4, display:'flex', gap:1.5, overflow:'hidden', cursor:'pointer', marginBottom:3 }}>
        {items.length === 0
          ? <div style={{ flex:1, background:`${color}22`, borderRadius:4, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <span style={{ color:'#374151', fontSize:10 }}>aguardando...</span>
            </div>
          : items.map((item, i) => (
            <div key={i}
              onClick={() => onSelect(i)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              title={`#${item.scene_number || (i+1)}`}
              style={{
                flex: item.duration_seconds || 1, minWidth:8,
                background: i === selectedIdx ? color : hovered === i ? `${color}cc` : `${color}88`,
                borderRadius:2, transition:'background .12s',
                outline: i === selectedIdx ? `2px solid ${color}` : 'none', outlineOffset:-1
              }} />
          ))
        }
      </div>
      {/* Waveform MP3 */}
      <div style={{ height:20, background:'rgba(255,255,255,.03)', borderRadius:4, overflow:'hidden', position:'relative', display:'flex', alignItems:'center' }}>
        <span style={{ position:'absolute', left:6, fontSize:8, color:'#374151', whiteSpace:'nowrap', zIndex:1 }}>
          🎵 {fileName || 'audio.mp3'}
        </span>
        <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', paddingLeft:88, paddingRight:4, gap:0.5 }}>
          {Array.from({ length:130 }).map((_,i) => (
            <div key={i} style={{ flex:1, background:'rgba(249,115,22,.38)', borderRadius:1, height:`${18+((i*41+7)%52)}%` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════
// 🎛️ EDITOR PREVIEW — sub-abas Shotlist / Imagens / Videos
// ══════════════════════════════════════════════════════
function EditorPanel({ scenes, completedClips, jobStatus, onEditScene, onEditClip, fileName }) {
  const [subTab,      setSubTab]      = useState(0)
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [modal,       setModal]       = useState(null) // null | number

  const shotItems  = scenes || []
  const imageItems = (scenes || []).filter(s => s.image_url)
  const videoItems = (completedClips || []).filter(c => c.success && c.video_url)
  const allItems   = [shotItems, imageItems, videoItems]
  const counts     = allItems.map(a => a.length)
  const currentItems = allItems[subTab]
  const selectedItem = currentItems[selectedIdx] || null
  const tabColors    = ['#f97316','#22c55e','#a78bfa']
  const color        = tabColors[subTab]

  const switchSub  = (idx) => { setSubTab(idx); setSelectedIdx(0); setModal(null) }
  const openModal  = (idx) => { setSelectedIdx(idx); setModal(idx) }
  const closeModal = ()    => setModal(null)
  const navModal   = (d)   => {
    const next = Math.max(0, Math.min(currentItems.length-1, modal+d))
    setModal(next); setSelectedIdx(next)
  }

  return (
    <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, overflow:'hidden', animation:'fadeUp .4s ease' }}>

      {/* Header */}
      <div style={{ padding:'12px 18px', display:'flex', alignItems:'center', justifyContent:'space-between', borderBottom:'1px solid rgba(255,255,255,.07)' }}>
        <span style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:13, letterSpacing:2, color:'#fff' }}>EDITOR PREVIEW</span>
        <div style={{ display:'flex', gap:4 }}>
          {['Shotlist','Imagens','Videos'].map((label, idx) => (
            <button key={idx} onClick={() => switchSub(idx)}
              style={{ padding:'5px 13px', borderRadius:7, fontSize:12, fontWeight:600, cursor:'pointer',
                background: subTab===idx ? 'rgba(255,255,255,.1)' : 'transparent',
                border: subTab===idx ? '1px solid rgba(255,255,255,.18)' : '1px solid rgba(255,255,255,.06)',
                color: subTab===idx ? '#fff' : '#6b7280', transition:'all .2s' }}>
              {label} ({counts[idx]})
            </button>
          ))}
        </div>
      </div>

      {/* Preview Area */}
      <div style={{ position:'relative', background:'#050508', minHeight:260 }}>

        {/* SHOTLIST preview */}
        {subTab === 0 && selectedItem && modal === null && (
          <div style={{ padding:'20px 24px', animation:'fadeUp .3s ease' }}>
            <div style={{ color:'#9ca3af', fontSize:12, fontWeight:600, marginBottom:16 }}>Shot List Preview</div>
            <div style={{ marginBottom:14 }}>
              <div style={{ color:'#4b5563', fontSize:9, fontWeight:700, letterSpacing:1, marginBottom:5 }}>START FRAME</div>
              <p style={{ color:'#d1d5db', fontSize:13, lineHeight:1.65 }}>{resolvePrompt(selectedItem) || selectedItem.camera_movement || '—'}</p>
            </div>
            <div>
              <div style={{ color:'#4b5563', fontSize:9, fontWeight:700, letterSpacing:1, marginBottom:5 }}>ACTION & CAMERA</div>
              <p style={{ color:'#d1d5db', fontSize:13, lineHeight:1.65 }}>{selectedItem.camera_movement || selectedItem.mood || '—'}</p>
            </div>
          </div>
        )}

        {/* IMAGENS preview */}
        {subTab === 1 && selectedItem && modal === null && (
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:260, padding:16, animation:'fadeUp .3s ease' }}>
            {selectedItem.image_url
              ? <img src={selectedItem.image_url} alt="" style={{ maxHeight:240, maxWidth:'100%', objectFit:'contain', borderRadius:6 }} />
              : <div style={{ color:'#4b5563', fontSize:13 }}>Sem imagem</div>}
          </div>
        )}

        {/* VIDEOS preview */}
        {subTab === 2 && selectedItem && modal === null && (
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:260, padding:16, animation:'fadeUp .3s ease' }}>
            {selectedItem.video_url
              ? <video key={selectedItem.video_url} src={selectedItem.video_url} controls style={{ maxHeight:240, maxWidth:'100%', borderRadius:6 }} />
              : <div style={{ color:'#4b5563', fontSize:13 }}>Sem vídeo</div>}
          </div>
        )}

        {/* Empty state */}
        {(currentItems.length === 0) && modal === null && (
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:260, flexDirection:'column', gap:10, color:'#374151' }}>
            <div style={{ fontSize:34 }}>{subTab===0 ? '📋' : subTab===1 ? '🖼️' : '🎥'}</div>
            <div style={{ fontSize:13 }}>Aguardando geração...</div>
          </div>
        )}

        {/* ══ MODAL OVERLAY ══ */}
        {modal !== null && (() => {
          const item  = currentItems[modal]
          if (!item) return null
          const total = currentItems.length
          return (
            <div style={{ position:'absolute', inset:0, background:'rgba(10,10,14,.97)', zIndex:20, display:'flex', flexDirection:'column', padding:'18px 20px', overflowY:'auto', animation:'fadeUp .25s ease' }}>
              <button onClick={closeModal}
                style={{ position:'absolute', top:12, right:14, background:'rgba(255,255,255,.07)', border:'none', borderRadius:7, color:'#9ca3af', fontSize:14, cursor:'pointer', padding:'3px 10px' }}>✕</button>

              {/* SHOT modal */}
              {subTab === 0 && (
                <>
                  <div style={{ color:'#fff', fontSize:14, fontWeight:700, marginBottom:14 }}>Shot #{item.scene_number}</div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, flex:1 }}>
                    <div style={{ background:'rgba(255,255,255,.04)', borderRadius:12, padding:'14px 16px' }}>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:700, letterSpacing:.5, marginBottom:12 }}>Shot Details</div>
                      <div style={{ color:'#4b5563', fontSize:9, letterSpacing:.5, marginBottom:3 }}>TIME</div>
                      <div style={{ color:'#d1d5db', fontSize:12, marginBottom:10 }}>{item.duration_seconds || 5}s</div>
                      <div style={{ color:'#4b5563', fontSize:9, letterSpacing:.5, marginBottom:3 }}>ACTION & CONTENT</div>
                      <div style={{ color:'#d1d5db', fontSize:12, lineHeight:1.6, marginBottom:10 }}>{item.camera_movement || item.mood || '—'}</div>
                      <div style={{ color:'#4b5563', fontSize:9, letterSpacing:.5, marginBottom:3 }}>TYPE</div>
                      <div style={{ color:'#22c55e', fontSize:12, fontWeight:600 }}>A-roll</div>
                    </div>
                    <div style={{ background:'rgba(255,255,255,.04)', borderRadius:12, padding:'14px 16px' }}>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:700, letterSpacing:.5, marginBottom:10 }}>Prompt Content</div>
                      <p style={{ color:'#d1d5db', fontSize:12, lineHeight:1.7 }}>{resolvePrompt(item) || '—'}</p>
                    </div>
                  </div>
                </>
              )}

              {/* IMAGEM modal */}
              {subTab === 1 && (
                <>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
                    <span style={{ color:'#fff', fontSize:14, fontWeight:700 }}>Cena #{item.scene_number}</span>
                    <span style={{ background:'rgba(34,197,94,.15)', color:'#22c55e', fontSize:9, fontWeight:700, borderRadius:5, padding:'2px 7px' }}>Sucesso</span>
                  </div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, flex:1 }}>
                    <div>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, marginBottom:8 }}>Imagem gerada</div>
                      {item.image_url && <img src={item.image_url} alt="" style={{ width:'100%', borderRadius:10, display:'block', marginBottom:8, maxHeight:190, objectFit:'cover' }} />}
                      <div style={{ display:'flex', gap:6 }}>
                        <button onClick={() => { onEditScene && onEditScene(item); closeModal() }}
                          style={{ flex:1, padding:'7px', background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:8, color:'#9ca3af', fontSize:10, cursor:'pointer' }}>✏️ Editar</button>
                        <a href={item.image_url} download={`cena_${item.scene_number}.jpg`} target="_blank" rel="noreferrer"
                          style={{ flex:1, padding:'7px', background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:8, color:'#9ca3af', fontSize:10, cursor:'pointer', textDecoration:'none', textAlign:'center' }}>⬇ Baixar</a>
                      </div>
                    </div>
                    <div>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, marginBottom:8 }}>Conteúdo do prompt</div>
                      <div style={{ background:'rgba(255,255,255,.04)', borderRadius:10, padding:'12px', maxHeight:230, overflowY:'auto' }}>
                        <p style={{ color:'#d1d5db', fontSize:12, lineHeight:1.7 }}>{resolvePrompt(item) || '—'}</p>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* VÍDEO modal */}
              {subTab === 2 && (
                <>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
                    <span style={{ color:'#fff', fontSize:14, fontWeight:700 }}>Vídeo #{item.scene_number}</span>
                    <span style={{ background:'rgba(34,197,94,.15)', color:'#22c55e', fontSize:9, fontWeight:700, borderRadius:5, padding:'2px 7px' }}>Sucesso</span>
                  </div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, flex:1 }}>
                    <div>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, marginBottom:8 }}>Vídeo gerado</div>
                      <video key={item.video_url} src={item.video_url} controls style={{ width:'100%', borderRadius:10, display:'block', maxHeight:190, marginBottom:8 }} />
                      <div style={{ display:'flex', gap:6 }}>
                        <button onClick={() => { onEditClip && onEditClip(item); closeModal() }}
                          style={{ flex:1, padding:'7px', background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:8, color:'#9ca3af', fontSize:10, cursor:'pointer' }}>✏️ Editar</button>
                        <a href={item.video_url} download={`video_${item.scene_number}.mp4`} target="_blank" rel="noreferrer"
                          style={{ flex:1, padding:'7px', background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:8, color:'#9ca3af', fontSize:10, cursor:'pointer', textDecoration:'none', textAlign:'center' }}>⬇ Baixar</a>
                      </div>
                    </div>
                    <div>
                      <div style={{ color:'#9ca3af', fontSize:11, fontWeight:600, marginBottom:8 }}>Conteúdo do prompt</div>
                      <div style={{ background:'rgba(255,255,255,.04)', borderRadius:10, padding:'12px', maxHeight:230, overflowY:'auto' }}>
                        <p style={{ color:'#d1d5db', fontSize:12, lineHeight:1.7 }}>{resolvePrompt(item) || '—'}</p>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Navegação */}
              <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:14, marginTop:16 }}>
                <button onClick={() => navModal(-1)} disabled={modal === 0}
                  style={{ background:'rgba(255,255,255,.07)', border:'none', borderRadius:6, color: modal===0 ? '#374151' : '#9ca3af', fontSize:18, cursor: modal===0 ? 'default':'pointer', padding:'3px 12px' }}>‹</button>
                <span style={{ color:'#9ca3af', fontSize:12 }}>{modal+1}/{total}</span>
                <button onClick={() => navModal(1)} disabled={modal === total-1}
                  style={{ background:'rgba(255,255,255,.07)', border:'none', borderRadius:6, color: modal===total-1 ? '#374151' : '#9ca3af', fontSize:18, cursor: modal===total-1 ? 'default':'pointer', padding:'3px 12px' }}>›</button>
              </div>
            </div>
          )
        })()}
      </div>

      {/* Timeline */}
      <EditorTimeline
        items={currentItems}
        selectedIdx={selectedIdx}
        onSelect={openModal}
        color={color}
        fileName={fileName}
      />
    </div>
  )
}

// ══════════════════════════════════════════════════════
// 🏠 DASHBOARD PRINCIPAL
// ══════════════════════════════════════════════════════
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
  // ✅ FIX B: armazena lipsync_clips para passar ao LipSyncPanel
  const [lipSyncClips,   setLipSyncClips]   = useState(null)
  const [cancelled,      setCancelled]      = useState(false)
  const [editModal,      setEditModal]      = useState(null)
  const [activeTab,      setActiveTab]      = useState(2) // 0=Resultado 1=Editor 2=Tela
  const pollRef = useRef()

  useEffect(() => {
    const wake = async () => {
      try {
        const res = await fetch(`${API_URL}/api/health`)
        if (res.ok) {
          setServerReady(true)
          const savedId   = localStorage.getItem('clipvox_active_job')
          const savedName = localStorage.getItem('clipvox_active_name')
          if (savedId) {
            try {
              const r = await fetch(`${API_URL}/api/videos/status/${savedId}`)
              if (r.ok) {
                const data = await r.json()
                const isActive = ['processing','pending'].includes(data.status)
                  || ['processing','retrying'].includes(data.videos_status)
                  || data.lipsync_status === 'processing'
                  || data.merge_status === 'processing'
                if (isActive || data.status === 'completed') {
                  handleResume(savedId, data, savedName)
                } else {
                  localStorage.removeItem('clipvox_active_job')
                  localStorage.removeItem('clipvox_active_name')
                }
              }
            } catch(e) {}
          }
          return
        }
      } catch(e) {}
      setTimeout(wake, 5000)
    }
    wake()
  }, [])

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  useEffect(() => {
    if (!jobStatus) return
    if (jobStatus.videos_status === 'completed' && jobStatus.video_clips) {
      setCompletedClips(jobStatus.video_clips)
    }
    if (jobStatus.lipsync_status === 'completed' && jobStatus.lipsync_clips?.some(c => c.success)) {
      setLipSyncDone(true)
      setLipSyncUrl(jobStatus.lipsync_url || null)
      setLipSyncClips(jobStatus.lipsync_clips)
    }
    // ✅ FIX C: atualiza lipSyncClips se houver regen individual em andamento
    if (jobStatus.lipsync_clips) {
      setLipSyncClips(jobStatus.lipsync_clips)
    }
    // Vai para aba Resultado automaticamente quando merge concluir
    if (jobStatus.merge_status === 'completed' && jobStatus.merge_url) {
      setActiveTab(0)
    }
  }, [jobStatus])

  const handleResume = (id, data, savedName) => {
    setJobId(id)
    setJobStatus(data)
    const name = savedName || data?.file_name || data?.audio_filename || `job-${id.slice(0,8)}`
    setFileName(name)
    setPhase('processing')
    localStorage.setItem('clipvox_active_job', id)
    localStorage.setItem('clipvox_active_name', name)
    try {
      const hist = JSON.parse(localStorage.getItem('clipvox_history') || '[]')
      if (!hist.find(h => h.id === id)) {
        localStorage.setItem('clipvox_history', JSON.stringify(
          [{ id, name, date: new Date().toLocaleDateString('pt-BR') }, ...hist].slice(0,20)
        ))
      }
    } catch(e) {}
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/videos/status/${id}`)
        if (!res.ok) return
        const status = await res.json()
        setJobStatus(status)
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollRef.current)
        }
      } catch(e) {}
    }, 3000)
  }

  const startGeneration = async ({ file, desc, style, duration, aspectRatio, resolution, refImages }) => {
    try {
      setFileName(file.name); setPhase('processing'); setCredits(c => c - 100)
      setCompletedClips(null); setLipSyncDone(false); setLipSyncUrl(null); setLipSyncClips(null)
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
        alert(fetchErr.name === 'AbortError' ? 'Servidor demorando — aguarde 30s.' : 'Não foi possível conectar.')
        setPhase('upload'); return
      }
      if (!response.ok) {
        alert(response.status === 504 ? 'Servidor em cold start. Aguarde 30s.' : `Erro ${response.status}.`)
        setPhase('upload'); return
      }
      const data = await response.json()
      if (!data.job_id) { alert('Resposta inesperada.'); setPhase('upload'); return }
      setJobId(data.job_id)
      localStorage.setItem('clipvox_active_job', data.job_id)
      localStorage.setItem('clipvox_active_name', file.name)
      try {
        const hist = JSON.parse(localStorage.getItem('clipvox_history') || '[]')
        const entry = { id: data.job_id, name: file.name, date: new Date().toLocaleDateString('pt-BR') }
        localStorage.setItem('clipvox_history', JSON.stringify(
          [entry, ...hist.filter(h => h.id !== data.job_id)].slice(0, 20)
        ))
      } catch(e) {}
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
        } catch(e) {}
      }, 2000)
    } catch(error) {
      alert('Erro inesperado.'); setPhase('upload')
    }
  }

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    localStorage.removeItem('clipvox_active_job')
    localStorage.removeItem('clipvox_active_name')
    setPhase('upload'); setJobId(null); setJobStatus(null); setFileName('')
    setCompletedClips(null); setLipSyncDone(false); setLipSyncUrl(null)
    setLipSyncClips(null); setCancelled(false)
  }

  const handleCancel = async () => {
    if (!jobId || cancelled) return
    try {
      await fetch(`${API_URL}/api/videos/cancel/${jobId}`, { method: 'POST' })
      setCancelled(true)
      if (pollRef.current) clearInterval(pollRef.current)
    } catch(e) {}
  }

  const handleVideosCompleted = (clips) => {
    if (clips && clips.some(c => c.success)) setCompletedClips(clips)
  }

  const handleRegenerated = async () => {
    if (!jobId) return
    try {
      const res = await fetch(`${API_URL}/api/videos/status/${jobId}`)
      if (res.ok) setJobStatus(await res.json())
    } catch(e) {}
  }

  // ✅ FIX B+C: onLipSyncCompleted recebe também os clips
  const handleLipSyncCompleted = (url, clips) => {
    setLipSyncDone(true)
    setLipSyncUrl(url || null)
    if (clips) setLipSyncClips(clips)
  }

  // ✅ FIX B+C: chama o backend para refazer lip sync de uma cena individual
  // e inicia polling para detectar quando lipsync_regenerating virar false
  const handleRetrySyncClip = async (sceneNumber) => {
    if (!jobId) return
    try {
      const formData = new FormData()
      formData.append('model', 'kling')
      const res = await fetch(`${API_URL}/api/videos/regen-lipsync/${jobId}/${sceneNumber}`, {
        method: 'POST', body: formData
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(err.detail || `Erro ao refazer lip sync da cena ${sceneNumber}`)
        return
      }
      // Marca localmente como regenerando enquanto aguarda o backend
      setLipSyncClips(prev => (prev || []).map(c =>
        c.scene_number === sceneNumber ? { ...c, lipsync_regenerating: true } : c
      ))
      // Polling até lipsync_regenerating = false para essa cena
      const pollRegen = setInterval(async () => {
        try {
          const r = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const s = await r.json()
          const updatedClip = (s.lipsync_clips || []).find(c => c.scene_number === sceneNumber)
          if (updatedClip && !updatedClip.lipsync_regenerating) {
            clearInterval(pollRegen)
            setLipSyncClips(s.lipsync_clips)
          }
        } catch(e) {}
      }, 5000)
      // Timeout de segurança: para de polling após 10 minutos
      setTimeout(() => clearInterval(pollRegen), 600000)
    } catch(e) {
      alert('Erro ao iniciar retry de lip sync: ' + e.message)
    }
  }

  // ✅ FIX A: ao abrir modal de vídeo, enriquece o clip com o prompt da cena correspondente
  const handleEditClip = (clip) => {
    const scene = jobStatus?.scenes?.find(s => s.scene_number === clip.scene_number)
    const enrichedClip = {
      ...clip,
      prompt: resolvePrompt(clip) || resolvePrompt(scene),
    }
    setEditModal({ item: enrichedClip, type: 'video' })
  }

  const lipSyncWasStuck = jobStatus?.lipsync_status === 'processing' && !lipSyncDone

  if (phase === 'upload') {
    return (
      <div style={{ fontFamily:"'DM Sans',sans-serif", background:'#0a0a0e', color:'#fff', minHeight:'100vh' }}>
        <style>{CSS}</style>
        <Navbar onBack={onBack} credits={credits} />
        {!serverReady && (
          <div style={{ background:'rgba(249,115,22,.08)', borderBottom:'1px solid rgba(249,115,22,.2)', padding:'10px 24px', textAlign:'center', display:'flex', alignItems:'center', justifyContent:'center', gap:8 }}>
            <div style={{ width:12, height:12, border:'2px solid rgba(249,115,22,.3)', borderTop:'2px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
            <span style={{ color:'#f97316', fontSize:12 }}>Conectando ao servidor...</span>
          </div>
        )}
        <UploadZone onStart={startGeneration} />
        <HistoryPanel onResume={handleResume} />
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
          {/* ── 3 ABAS FUNCIONAIS ── */}
          <div style={{ display:'flex', gap:6, marginBottom:18 }}>
            {[
              { label:'Resultado', icon:'🎬', idx:0 },
              { label:'Editor',    icon:'🎛️', idx:1 },
              { label:'Tela',      icon:'🗺️', idx:2 },
            ].map(({ label, icon, idx }) => (
              <div key={idx} onClick={() => setActiveTab(idx)}
                style={{
                  padding:'7px 16px', borderRadius:8, fontSize:13, fontWeight:500, cursor:'pointer',
                  display:'flex', alignItems:'center', gap:6,
                  background: activeTab===idx ? 'rgba(249,115,22,.1)' : 'rgba(255,255,255,.04)',
                  border: activeTab===idx ? '1px solid rgba(249,115,22,.3)' : '1px solid rgba(255,255,255,.06)',
                  color: activeTab===idx ? '#f97316' : '#6b7280',
                  transition:'all .2s'
                }}>
                <span>{icon}</span><span>{label}</span>
              </div>
            ))}
          </div>

          {/* ══ ABA 0: RESULTADO ══ */}
          {activeTab === 0 && (
            <div style={{ display:'flex', flexDirection:'column', gap:16, animation:'fadeUp .4s ease' }}>
              {jobStatus?.merge_url ? (
                /* Vídeo final disponível */
                <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(34,197,94,.2)', borderRadius:16, overflow:'hidden' }}>
                  <div style={{ padding:'14px 20px', display:'flex', alignItems:'center', justifyContent:'space-between', borderBottom:'1px solid rgba(255,255,255,.06)' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                      <span style={{ fontSize:20 }}>🎉</span>
                      <div>
                        <div style={{ fontFamily:"'Bebas Neue',sans-serif", fontSize:14, letterSpacing:2, color:'#fff' }}>VIDEOCLIPE FINAL</div>
                        <div style={{ color:'#22c55e', fontSize:11 }}>Pronto para download e publicação</div>
                      </div>
                    </div>
                    <div style={{ display:'flex', gap:8 }}>
                      <a href={jobStatus.merge_url} target="_blank" rel="noreferrer"
                        style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'8px 16px', background:'rgba(34,197,94,.1)', border:'1px solid rgba(34,197,94,.3)', color:'#22c55e', borderRadius:10, fontSize:12, fontWeight:600, textDecoration:'none' }}>
                        ▶ Assistir
                      </a>
                      <button onClick={() => forceDownload(jobStatus.merge_url, `clipvox_${jobId}.mp4`)}
                        style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'8px 16px', background:'rgba(249,115,22,.1)', border:'1px solid rgba(249,115,22,.3)', color:'#f97316', borderRadius:10, fontSize:12, fontWeight:600, cursor:'pointer' }}>
                        ⬇ Baixar MP4
                      </button>
                    </div>
                  </div>
                  <video src={jobStatus.merge_url} controls style={{ width:'100%', display:'block', maxHeight:480, background:'#000' }} />
                  <div style={{ padding:'12px 20px', display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10 }}>
                    {[
                      { label:'🎵 Música',  value: jobStatus.audio_filename || fileName },
                      { label:'⏱️ Duração', value: jobStatus.audio_duration ? `${Math.floor(jobStatus.audio_duration/60)}:${String(Math.floor(jobStatus.audio_duration%60)).padStart(2,'0')}` : '—' },
                      { label:'🎬 Cenas',   value: `${jobStatus.scenes?.length || 0} cenas geradas` },
                    ].map((item, i) => (
                      <div key={i} style={{ background:'rgba(255,255,255,.04)', borderRadius:10, padding:'10px 12px' }}>
                        <div style={{ color:'#6b7280', fontSize:10, marginBottom:3 }}>{item.label}</div>
                        <div style={{ color:'#fff', fontSize:12, fontWeight:600, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Ainda em produção */
                <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:'72px 24px', textAlign:'center' }}>
                  <div style={{ fontSize:52, marginBottom:16 }}>🎬</div>
                  <div style={{ color:'#fff', fontSize:16, fontWeight:600, marginBottom:8 }}>Videoclipe em produção</div>
                  <div style={{ color:'#6b7280', fontSize:13, marginBottom:6 }}>Acompanhe o progresso na aba <strong style={{ color:'#f97316' }}>Tela</strong></div>
                  <div style={{ color:'#4b5563', fontSize:12 }}>O vídeo final aparecerá aqui após o Merge Final</div>
                  {jobStatus?.current_step && (
                    <div style={{ marginTop:20, display:'inline-flex', alignItems:'center', gap:8, background:'rgba(249,115,22,.08)', border:'1px solid rgba(249,115,22,.2)', borderRadius:8, padding:'8px 16px' }}>
                      <div style={{ width:8, height:8, borderRadius:'50%', background:'#f97316', animation:'pulse 1.4s ease infinite' }} />
                      <span style={{ color:'#f97316', fontSize:12 }}>
                        {({'plan':'Planejando...','analyzing':'Analisando áudio...','creative':'Gerando conceito...','scenes':'Gerando imagens...','segments':'Gerando vídeos...','merge':'Merge final...'})[jobStatus.current_step] || 'Processando...'}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ══ ABA 1: EDITOR ══ */}
          {activeTab === 1 && (
            <EditorPanel
              scenes={jobStatus?.scenes}
              completedClips={completedClips}
              jobStatus={jobStatus}
              onEditScene={sc => setEditModal({ item: sc, type: 'scene' })}
              onEditClip={handleEditClip}
              fileName={fileName}
            />
          )}

          {/* ══ ABA 2: TELA — conteúdo original do Canvas ══ */}
          {activeTab === 2 && (<>

          {!jobStatus && (
            <div style={{ background:'rgba(16,16,24,.85)', border:'1px solid rgba(255,255,255,.07)', borderRadius:16, padding:'56px 24px', textAlign:'center' }}>
              {!cancelled ? (
                <>
                  <div style={{ width:38, height:38, margin:'0 auto 14px', border:'3px solid rgba(255,255,255,.1)', borderTop:'3px solid #f97316', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
                  <p style={{ color:'#6b7280', fontSize:14, marginBottom:16 }}>Processando sua música com IA...</p>
                  <button onClick={handleCancel} style={{ background:'rgba(239,68,68,.1)', border:'1px solid rgba(239,68,68,.3)', borderRadius:10, padding:'8px 20px', color:'#ef4444', fontSize:12, cursor:'pointer' }}>🛑 Cancelar geração</button>
                </>
              ) : (
                <><div style={{ fontSize:32, marginBottom:10 }}>🛑</div><p style={{ color:'#ef4444', fontSize:14, marginBottom:12 }}>Geração cancelada</p>
                <button onClick={reset} style={{ background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.1)', borderRadius:10, padding:'8px 20px', color:'#fff', fontSize:13, cursor:'pointer' }}>🔄 Novo Videoclipe</button></>
              )}
            </div>
          )}

          {jobStatus?.creative_concept && <CreativeConceptCard concept={jobStatus.creative_concept} />}
          {jobStatus?.scenes && (
            <div style={{ marginTop:16 }}>
              <ScenesGrid scenes={jobStatus.scenes} jobId={jobId}
                onEditScene={sc => setEditModal({ item: sc, type: 'scene' })} />
            </div>
          )}

          {jobStatus?.status === 'completed' && jobId && (
            <>
              <VideoClipsPanel
                jobId={jobId}
                jobStatus={jobStatus}
                onVideosCompleted={handleVideosCompleted}
                onCancel={handleCancel}
                onEditClip={handleEditClip}
              />

              {(completedClips?.some(c => c.success) || lipSyncWasStuck) && !lipSyncDone && (
                <LipSyncPanel
                  jobId={jobId}
                  videoClips={completedClips}
                  onLipSyncCompleted={handleLipSyncCompleted}
                  initialLipSyncStatus={jobStatus?.lipsync_status}
                  onCancel={handleCancel}
                  onRetrySyncClip={handleRetrySyncClip}
                  lipSyncClips={lipSyncClips}
                />
              )}

              {lipSyncDone && lipSyncClips?.some(c => c.lipsync_error) && (
                <LipSyncPanel
                  jobId={jobId}
                  videoClips={completedClips}
                  onLipSyncCompleted={handleLipSyncCompleted}
                  initialLipSyncStatus="completed"
                  initialLipUrl={lipSyncUrl}
                  onCancel={handleCancel}
                  onRetrySyncClip={handleRetrySyncClip}
                  lipSyncClips={lipSyncClips}
                />
              )}

              {completedClips?.some(c => c.success) && lipSyncDone && (
                <MergePanel
                  jobId={jobId}
                  videoClips={completedClips}
                  lipSyncUrl={lipSyncUrl}
                  initialMergeStatus={jobStatus?.merge_status}
                  initialMergeUrl={jobStatus?.merge_url}
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

          </>)}
        </div>
      </div>

      {editModal && (
        <SceneEditModal
          item={editModal.item}
          type={editModal.type}
          jobId={jobId}
          onClose={() => setEditModal(null)}
          onRegenerated={handleRegenerated}
        />
      )}
    </div>
  )
}
