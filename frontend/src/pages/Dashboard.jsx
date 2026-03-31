import { useEffect, useMemo, useRef, useState } from 'react'

const API_URL = 'https://clipvox-backend.onrender.com'

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600;700&display=swap');
*{box-sizing:border-box}
body{margin:0;background:#07080d;color:#fff;font-family:'DM Sans',system-ui,sans-serif}
button,input,select,textarea{font:inherit}
a{color:inherit;text-decoration:none}
::-webkit-scrollbar{width:7px;height:7px}
::-webkit-scrollbar-thumb{background:#2a3042;border-radius:999px}
::-webkit-scrollbar-track{background:#0d1119}
@keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
.cv-app{min-height:100vh;background:radial-gradient(circle at top,rgba(56,189,248,.08),transparent 24%),linear-gradient(180deg,#07080d 0%,#0b0f17 100%)}
.cv-nav{position:sticky;top:0;z-index:20;display:flex;justify-content:space-between;align-items:center;padding:16px 26px;border-bottom:1px solid rgba(255,255,255,.06);background:rgba(7,8,13,.88);backdrop-filter:blur(12px)}
.cv-brand{display:flex;align-items:center;gap:12px}
.cv-brand-title{font-family:'Bebas Neue',sans-serif;letter-spacing:3px;font-size:22px}
.cv-container{max-width:1360px;margin:0 auto;padding:28px 22px 72px}
.cv-shell{display:grid;grid-template-columns:320px minmax(0,1fr);gap:22px;align-items:start}
.cv-panel{background:rgba(17,21,31,.88);border:1px solid rgba(255,255,255,.07);border-radius:22px;box-shadow:0 16px 48px rgba(0,0,0,.25)}
.cv-sidebar{padding:18px;position:sticky;top:88px}
.cv-main{padding:18px}
.cv-section-title{font-family:'Bebas Neue',sans-serif;letter-spacing:1.5px;font-size:24px;margin:0 0 6px}
.cv-muted{color:#8b93a7;font-size:13px;line-height:1.5}
.cv-upload{display:grid;gap:14px;margin-top:18px}
.cv-input,.cv-textarea,.cv-select{width:100%;border:1px solid rgba(255,255,255,.08);background:#0b111a;color:#fff;border-radius:14px;padding:12px 14px;outline:none}
.cv-textarea{min-height:110px;resize:vertical}
.cv-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cv-btn{border:none;border-radius:14px;padding:12px 16px;font-weight:700;cursor:pointer;transition:.2s ease;display:inline-flex;align-items:center;gap:8px;justify-content:center}
.cv-btn:hover{transform:translateY(-1px)}
.cv-btn:disabled{opacity:.45;cursor:not-allowed;transform:none}
.cv-btn-primary{background:linear-gradient(135deg,#4f46e5,#2563eb);color:#fff}
.cv-btn-secondary{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);color:#fff}
.cv-btn-orange{background:linear-gradient(135deg,#f97316,#ea580c);color:#fff}
.cv-btn-green{background:linear-gradient(135deg,#16a34a,#22c55e);color:#fff}
.cv-btn-red{background:rgba(239,68,68,.12);color:#fca5a5;border:1px solid rgba(239,68,68,.28)}
.cv-pills{display:flex;flex-wrap:wrap;gap:10px}
.cv-pill{padding:8px 12px;border-radius:999px;font-size:12px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.07);color:#c7cfdd}
.cv-status-list{display:grid;gap:10px;margin-top:16px}
.cv-status-item{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-radius:14px;background:#0d121b;border:1px solid rgba(255,255,255,.06)}
.cv-status-step{display:flex;align-items:center;gap:10px}
.cv-step-dot{width:11px;height:11px;border-radius:999px;background:#263045}
.cv-step-dot.active{background:#22c55e;box-shadow:0 0 0 5px rgba(34,197,94,.12)}
.cv-step-dot.pending{background:#f59e0b;box-shadow:0 0 0 5px rgba(245,158,11,.12)}
.cv-progress{height:9px;border-radius:999px;background:#0b1018;overflow:hidden;border:1px solid rgba(255,255,255,.06);margin-top:14px}
.cv-progress>div{height:100%;background:linear-gradient(90deg,#22c55e,#38bdf8)}
.cv-tabs{display:flex;justify-content:center;gap:10px;margin-bottom:18px}
.cv-tab{padding:12px 18px;border-radius:14px;background:#0f1420;border:1px solid rgba(255,255,255,.07);color:#9aa4ba;font-weight:700;cursor:pointer}
.cv-tab.active{background:rgba(255,255,255,.08);color:#fff}
.cv-header-card{padding:18px;border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.015));border:1px solid rgba(255,255,255,.07);margin-bottom:18px}
.cv-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.cv-grid{display:grid;gap:18px}
.cv-grid-2{grid-template-columns:1.2fr .8fr}
.cv-card{padding:18px;border-radius:18px;background:#0c1119;border:1px solid rgba(255,255,255,.07);animation:fadeUp .35s ease}
.cv-card-title{font-size:13px;letter-spacing:.8px;text-transform:uppercase;color:#f59e0b;font-weight:700;margin:0 0 12px}
.cv-video-box,.cv-image-box{width:100%;aspect-ratio:16/9;border-radius:16px;background:#05070b;border:1px solid rgba(255,255,255,.06);display:flex;align-items:center;justify-content:center;overflow:hidden}
 .cv-image-box img,.cv-video-box video{width:100%;height:100%;object-fit:cover;display:block}
.cv-empty{display:flex;align-items:center;justify-content:center;min-height:220px;border:1px dashed rgba(255,255,255,.12);border-radius:16px;color:#7b8599;background:rgba(255,255,255,.02)}
.cv-subtabs{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.cv-subtab{padding:9px 14px;border-radius:999px;background:#131a26;border:1px solid rgba(255,255,255,.07);color:#9aa4ba;font-weight:700;cursor:pointer}
.cv-subtab.active{background:#2b3448;color:#fff}
.cv-editor-layout{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}
.cv-editor-meta{display:grid;gap:12px}
.cv-timeline{margin-top:16px;padding:14px;border-radius:18px;background:#090d14;border:1px solid rgba(255,255,255,.06)}
.cv-track{display:flex;gap:3px;align-items:flex-end;height:72px;margin-top:8px}
.cv-bar{border-radius:6px 6px 2px 2px;min-width:12px;cursor:pointer;transition:.16s ease}
.cv-bar:hover{filter:brightness(1.08)}
.cv-bar.active{outline:2px solid rgba(255,255,255,.92)}
.cv-track-audio{height:46px;display:flex;gap:2px;align-items:center;padding-top:10px}
.cv-wave{width:4px;background:#94a3b8;border-radius:999px;opacity:.85}
.cv-label-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(249,115,22,.14);border:1px solid rgba(249,115,22,.25);padding:7px 10px;border-radius:10px;color:#fdba74;font-size:12px;font-weight:700}
.cv-segment-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.cv-thumb{border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.06);background:#0b111a;cursor:pointer}
.cv-thumb-media{width:100%;aspect-ratio:16/9;display:block;background:#05070b}
.cv-thumb-media img,.cv-thumb-media video{width:100%;height:100%;object-fit:cover}
.cv-thumb-body{padding:10px 12px}
.cv-flow{display:grid;gap:18px}
.cv-flow-card{padding:18px;border-radius:20px;background:#0b111a;border:1px solid rgba(255,255,255,.08);position:relative}
.cv-flow-card::before{content:'';position:absolute;left:22px;top:-18px;height:18px;width:2px;background:linear-gradient(180deg,transparent,#22c55e);opacity:.6}
.cv-flow-card:first-child::before{display:none}
.cv-flow-title{display:flex;align-items:center;gap:10px;font-weight:800;margin-bottom:12px}
.cv-swatches{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.cv-swatch{flex:1;min-width:90px;height:44px;border-radius:12px;border:1px solid rgba(255,255,255,.08);display:flex;align-items:flex-end;justify-content:center;padding-bottom:6px;font-size:10px;color:#e5e7eb;text-shadow:0 1px 2px rgba(0,0,0,.55)}
.cv-mini-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}
.cv-mini-card{border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.06);background:#0a0e16}
.cv-mini-card img,.cv-mini-card video{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.cv-mini-card div{padding:8px 10px;font-size:11px;color:#cbd5e1}
.cv-kv{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.cv-kv .cv-card{padding:14px}
.cv-kv-value{font-size:24px;font-weight:800;margin-top:6px}
.cv-hero-grid{display:grid;grid-template-columns:1.35fr .65fr;gap:18px}
.cv-note{padding:12px 14px;border-radius:14px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.22);color:#bfdbfe;font-size:13px}
.cv-resume{display:flex;gap:10px;margin-top:14px}
.cv-resume input{flex:1}
.cv-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;font-size:11px;font-weight:700;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.22);color:#86efac}
.cv-divider{height:1px;background:rgba(255,255,255,.06);margin:14px 0}
.cv-link{color:#93c5fd;text-decoration:underline;text-underline-offset:3px}
@media (max-width: 1180px){.cv-shell,.cv-hero-grid,.cv-grid-2,.cv-editor-layout{grid-template-columns:1fr}.cv-sidebar{position:static}}
@media (max-width: 760px){.cv-container{padding:18px 14px 50px}.cv-row,.cv-kv{grid-template-columns:1fr}.cv-tabs{justify-content:flex-start;overflow:auto;padding-bottom:4px}.cv-subtabs{overflow:auto;flex-wrap:nowrap}.cv-nav{padding:14px 16px}}
`

const STYLE_OPTIONS = [
  ['realistic', 'Fotorrealista'],
  ['cinematic', 'Cinemático'],
  ['animated', 'Animado'],
  ['retro', 'Retrô'],
  ['anime', 'Anime'],
  ['cyberpunk', 'Cyberpunk'],
]

function absUrl(url) {
  if (!url) return ''
  return /^https?:\/\//i.test(url) ? url : `${API_URL}${url}`
}

function resolvePrompt(item) {
  return item?.prompt || item?.prompt_used || item?.image_prompt || item?.scene_prompt || item?.visual_prompt || item?.visual_description || item?.description || ''
}

function getSceneImage(scene) {
  return absUrl(scene?.image_url || scene?.r2_url || scene?.url || '')
}

function getVideoUrl(clip) {
  return absUrl(clip?.video_url || clip?.url || '')
}

function num(v, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function buildSegmentRows(status) {
  const scenes = (status?.scenes || []).filter(Boolean)
  const segments = Array.isArray(status?.segments) ? status.segments : []
  if (segments.length) {
    return segments.map((seg, idx) => {
      const items = (seg.scenes_with_images && seg.scenes_with_images.length ? seg.scenes_with_images : scenes.filter(s => (seg.scenes || []).includes(s.scene_number))) || []
      const first = items[0] || {}
      const duration = num(seg.duration_seconds, items.reduce((a, s) => a + num(s.duration_seconds, 4), 0) || 4)
      return {
        id: seg.segment_number || idx + 1,
        label: `Shot ${idx + 1}`,
        duration,
        prompt: resolvePrompt(first),
        camera: first.camera_movement || seg.camera_movement || 'Sem câmera definida',
        mood: first.mood || seg.mood || 'N/A',
        imageUrl: getSceneImage(first),
        type: first.type || 'B-roll',
        sceneNumbers: items.map(s => s.scene_number),
      }
    })
  }
  return scenes.map((scene, idx) => ({
    id: scene.scene_number || idx + 1,
    label: `Shot ${scene.scene_number || idx + 1}`,
    duration: num(scene.duration_seconds, 4),
    prompt: resolvePrompt(scene),
    camera: scene.camera_movement || 'Sem câmera definida',
    mood: scene.mood || 'N/A',
    imageUrl: getSceneImage(scene),
    type: scene.type || 'B-roll',
    sceneNumbers: [scene.scene_number || idx + 1],
  }))
}

function makeAudioWaves(total = 120) {
  return Array.from({ length: total }, (_, i) => 12 + Math.round(Math.abs(Math.sin(i * 0.53)) * 22 + Math.abs(Math.cos(i * 0.17)) * 8))
}

function saveHistory(jobId, name) {
  if (!jobId) return
  try {
    const current = JSON.parse(localStorage.getItem('clipvox_history') || '[]')
    const entry = { id: jobId, name: name || 'Videoclipe', date: new Date().toLocaleString('pt-BR') }
    const next = [entry, ...current.filter(i => i.id !== jobId)].slice(0, 10)
    localStorage.setItem('clipvox_history', JSON.stringify(next))
  } catch {}
}

function Logo() {
  return (
    <div className="cv-brand">
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <rect x="2" y="8" width="4" height="16" rx="2" fill="#fb923c" opacity=".65" />
        <rect x="9" y="4" width="4" height="24" rx="2" fill="#fb923c" opacity=".8" />
        <rect x="16" y="10" width="4" height="12" rx="2" fill="#fb923c" opacity=".6" />
        <rect x="23" y="3" width="4" height="26" rx="2" fill="#f97316" />
      </svg>
      <div className="cv-brand-title">CLIPVOX</div>
    </div>
  )
}

function TopNav({ onBack, hasJob }) {
  return (
    <div className="cv-nav">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button className="cv-btn cv-btn-secondary" onClick={onBack}>← Voltar</button>
        <Logo />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span className="cv-badge">{hasJob ? 'Workspace ativo' : 'Pronto para criar'}</span>
      </div>
    </div>
  )
}

function SidebarStatus({ status, onResume, resumeId, setResumeId, onReset, onCancel }) {
  const steps = [
    ['plan', 'Plano'],
    ['analyzing', 'Memória recuperada'],
    ['creative', 'Conceito criativo'],
    ['scenes', 'Cinematografia'],
    ['segments', 'Síntese de movimento'],
    ['done', 'Pós-produção'],
  ]
  const current = status?.current_step || ''
  const progress = num(status?.progress, 0)
  return (
    <div className="cv-sidebar cv-panel">
      <h2 className="cv-section-title">Workspace</h2>
      <p className="cv-muted">Upload, retomada de jobs e acompanhamento do pipeline completo do seu videoclipe.</p>

      {!status && (
        <>
          <div className="cv-divider" />
          <div className="cv-card-title">Retomar job</div>
          <div className="cv-resume">
            <input className="cv-input" placeholder="Cole o Job ID" value={resumeId} onChange={e => setResumeId(e.target.value)} />
            <button className="cv-btn cv-btn-primary" onClick={onResume} disabled={!resumeId.trim()}>Abrir</button>
          </div>
        </>
      )}

      {status && (
        <>
          <div className="cv-divider" />
          <div className="cv-card-title">Status do pipeline</div>
          <div className="cv-progress"><div style={{ width: `${progress}%` }} /></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, color: '#94a3b8', fontSize: 12 }}>
            <span>{progress.toFixed(0)}%</span>
            <span>{status.status || 'pending'}</span>
          </div>
          <div className="cv-status-list">
            {steps.map(([key, label]) => {
              const active = current === key || (key === 'done' && status.status === 'completed')
              const pending = !active && progress > 0 && progress < 100 && steps.findIndex(s => s[0] === key) <= steps.findIndex(s => s[0] === current)
              return (
                <div className="cv-status-item" key={key}>
                  <div className="cv-status-step">
                    <span className={`cv-step-dot ${active ? 'active' : pending ? 'pending' : ''}`}></span>
                    <span>{label}</span>
                  </div>
                  <span style={{ color: '#8b93a7', fontSize: 12 }}>{active ? '✓' : pending ? '…' : ''}</span>
                </div>
              )
            })}
          </div>

          <div className="cv-actions">
            <button className="cv-btn cv-btn-secondary" onClick={onReset}>Novo job</button>
            {status.status === 'processing' && <button className="cv-btn cv-btn-red" onClick={onCancel}>Cancelar</button>}
          </div>
        </>
      )}
    </div>
  )
}

function UploadPanel({ state, setState, onGenerate, busy }) {
  const setField = (k, v) => setState(prev => ({ ...prev, [k]: v }))
  const setRef = (index, file) => {
    setState(prev => {
      const refs = [...prev.refs]
      refs[index] = file || null
      return { ...prev, refs }
    })
  }
  return (
    <div className="cv-panel cv-main">
      <div className="cv-header-card">
        <h2 className="cv-section-title">Novo videoclipe</h2>
        <p className="cv-muted">Crie um job e acompanhe todas as etapas no formato Resultados, Editor e Tela.</p>
      </div>
      <div className="cv-grid">
        <div className="cv-card">
          <div className="cv-card-title">1. Áudio e direção</div>
          <div className="cv-upload">
            <input className="cv-input" type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac,.mp4" onChange={e => setField('audio', e.target.files?.[0] || null)} />
            <textarea className="cv-textarea" placeholder="Descreva a história, atmosfera, personagens e intenção emocional do videoclipe" value={state.description} onChange={e => setField('description', e.target.value)} />
            <div className="cv-row">
              <select className="cv-select" value={state.style} onChange={e => setField('style', e.target.value)}>
                {STYLE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <select className="cv-select" value={state.duration} onChange={e => setField('duration', e.target.value)}>
                <option value="full">Música completa</option>
                <option value="15">15s</option>
                <option value="30">30s</option>
                <option value="60">60s</option>
                <option value="120">120s</option>
              </select>
            </div>
            <div className="cv-row">
              <select className="cv-select" value={state.aspect_ratio} onChange={e => setField('aspect_ratio', e.target.value)}>
                <option value="16:9">16:9 · Horizontal</option>
                <option value="9:16">9:16 · Vertical</option>
                <option value="1:1">1:1 · Quadrado</option>
                <option value="4:3">4:3 · Clássico</option>
              </select>
              <select className="cv-select" value={state.resolution} onChange={e => setField('resolution', e.target.value)}>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </div>
          </div>
        </div>

        <div className="cv-card">
          <div className="cv-card-title">2. Referências visuais</div>
          <div className="cv-row">
            {[0, 1, 2].map(idx => (
              <input key={idx} className="cv-input" type="file" accept="image/*" onChange={e => setRef(idx, e.target.files?.[0] || null)} />
            ))}
          </div>
          <div className="cv-pills" style={{ marginTop: 12 }}>
            {state.refs.filter(Boolean).length === 0 ? <span className="cv-pill">Sem referências</span> : state.refs.map((file, idx) => file ? <span key={idx} className="cv-pill">Ref {idx + 1}: {file.name}</span> : null)}
          </div>
          <div className="cv-actions" style={{ marginTop: 16 }}>
            <button className="cv-btn cv-btn-primary" onClick={onGenerate} disabled={!state.audio || busy}>{busy ? 'Gerando…' : 'Gerar videoclipe'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ActionBar({ status, onGenerateClips, onRunLipSync, onMerge, onRetryClips, busy }) {
  const videoClips = status?.video_clips || []
  const successfulVideos = videoClips.filter(c => c?.success && c?.video_url)
  const lipsyncClips = status?.lipsync_clips || []
  const successfulLip = lipsyncClips.filter(c => c?.success && c?.video_url)
  return (
    <div className="cv-card" style={{ marginBottom: 18 }}>
      <div className="cv-card-title">Ações do pipeline</div>
      <div className="cv-actions">
        <button className="cv-btn cv-btn-primary" disabled={busy || status?.status !== 'completed'} onClick={onGenerateClips}>🎬 Gerar segmentos de vídeo</button>
        <button className="cv-btn cv-btn-secondary" disabled={busy || successfulVideos.length === 0} onClick={onRunLipSync}>🎤 Sincronizar fala</button>
        <button className="cv-btn cv-btn-green" disabled={busy || (successfulVideos.length === 0 && successfulLip.length === 0)} onClick={onMerge}>🏁 Gerar vídeo final</button>
        <button className="cv-btn cv-btn-orange" disabled={busy || videoClips.length === 0} onClick={onRetryClips}>🔁 Regenerar cenas com falha</button>
      </div>
      <div className="cv-pills" style={{ marginTop: 12 }}>
        <span className="cv-pill">Cenas: {(status?.scenes || []).filter(s => s?.success).length}</span>
        <span className="cv-pill">Vídeos: {successfulVideos.length}</span>
        <span className="cv-pill">Lip sync: {successfulLip.length}</span>
        <span className="cv-pill">Merge: {status?.merge_status || 'pending'}</span>
      </div>
    </div>
  )
}

function ResultsTab({ status, jobId }) {
  const finalUrl = absUrl(status?.merge_url)
  const fallbackDownload = `${API_URL}/api/videos/download/${jobId}`
  return (
    <div className="cv-grid">
      <div className="cv-card">
        <div className="cv-card-title">Resultado final</div>
        {finalUrl ? (
          <div className="cv-grid cv-grid-2">
            <div>
              <div className="cv-video-box">
                <video controls src={finalUrl} />
              </div>
              <div className="cv-actions">
                <a className="cv-btn cv-btn-primary" href={finalUrl} target="_blank" rel="noreferrer">▶ Visualizar</a>
                <a className="cv-btn cv-btn-green" href={fallbackDownload}>⬇ Download</a>
              </div>
            </div>
            <div className="cv-editor-meta">
              <div className="cv-note">Após o merge final, o vídeo fica disponível nesta aba para visualização e download, como você pediu.</div>
              <div className="cv-kv">
                <div className="cv-card"><div className="cv-muted">Status</div><div className="cv-kv-value">{status?.merge_status || 'pending'}</div></div>
                <div className="cv-card"><div className="cv-muted">Aspect Ratio</div><div className="cv-kv-value">{status?.config?.aspect_ratio || '16:9'}</div></div>
                <div className="cv-card"><div className="cv-muted">Resolução</div><div className="cv-kv-value">{status?.config?.resolution || '720p'}</div></div>
              </div>
              <div className="cv-card">
                <div className="cv-card-title">Arquivo final</div>
                <div className="cv-muted">{status?.output_file || `clipvox_${jobId}.mp4`}</div>
                <div style={{ marginTop: 10 }}>
                  <a className="cv-link" href={fallbackDownload}>Usar endpoint de download direto</a>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="cv-empty">O vídeo final aparecerá aqui depois do merge.</div>
        )}
      </div>
    </div>
  )
}

function EditorTab({ status, audioUrl, audioName }) {
  const scenes = (status?.scenes || []).filter(Boolean)
  const shotItems = buildSegmentRows(status)
  const imageItems = scenes.map((scene, idx) => ({
    id: scene.scene_number || idx + 1,
    label: `Cena ${scene.scene_number || idx + 1}`,
    duration: num(scene.duration_seconds, 4),
    prompt: resolvePrompt(scene),
    mediaUrl: getSceneImage(scene),
    camera: scene.camera_movement || 'Sem câmera definida',
    mood: scene.mood || 'N/A',
    type: scene.type || 'B-roll',
  }))
  const videoBase = ((status?.lipsync_clips || []).some(c => c?.success && c?.video_url) ? status?.lipsync_clips : status?.video_clips) || []
  const videoItems = videoBase.filter(Boolean).map((clip, idx) => {
    const scene = scenes.find(s => s.scene_number === clip.scene_number) || {}
    return {
      id: clip.scene_number || idx + 1,
      label: `Vídeo ${clip.scene_number || idx + 1}`,
      duration: num(clip.duration_seconds || scene.duration_seconds, 4),
      prompt: resolvePrompt(clip) || resolvePrompt(scene),
      mediaUrl: getVideoUrl(clip),
      camera: scene.camera_movement || 'Sem câmera definida',
      mood: scene.mood || 'N/A',
      type: clip.success ? 'A-roll' : 'Falhou',
      clip,
    }
  })

  const [subtab, setSubtab] = useState('shotlist')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const waves = useMemo(() => makeAudioWaves(150), [])

  const currentList = subtab === 'shotlist' ? shotItems : subtab === 'images' ? imageItems : videoItems
  const selected = currentList[selectedIndex] || currentList[0] || null
  const totalDuration = num(status?.audio_duration, currentList.reduce((acc, item) => acc + num(item.duration, 4), 0)) || 1

  useEffect(() => { setSelectedIndex(0) }, [subtab, status?.id])

  const colors = { shotlist: '#fbbf24', images: '#22c55e', videos: '#8b5cf6' }
  const isVideo = subtab === 'videos'

  return (
    <div className="cv-grid">
      <div className="cv-card">
        <div className="cv-card-title">Editor Preview</div>
        <div className="cv-subtabs">
          <button className={`cv-subtab ${subtab === 'shotlist' ? 'active' : ''}`} onClick={() => setSubtab('shotlist')}>Shotlist ({shotItems.length})</button>
          <button className={`cv-subtab ${subtab === 'images' ? 'active' : ''}`} onClick={() => setSubtab('images')}>Imagens ({imageItems.length})</button>
          <button className={`cv-subtab ${subtab === 'videos' ? 'active' : ''}`} onClick={() => setSubtab('videos')}>Vídeos ({videoItems.length})</button>
        </div>

        {selected ? (
          <div className="cv-editor-layout">
            <div>
              <div className={isVideo ? 'cv-video-box' : 'cv-image-box'}>
                {isVideo ? <video controls src={selected.mediaUrl} /> : selected.mediaUrl ? <img src={selected.mediaUrl} alt={selected.label} /> : <div className="cv-empty">Sem preview</div>}
              </div>
              <div className="cv-timeline">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8' }}>
                  <span>0:00</span>
                  <span>{Math.round(totalDuration)}s</span>
                </div>
                <div className="cv-track">
                  {currentList.map((item, idx) => {
                    const width = Math.max((num(item.duration, 4) / totalDuration) * 100, 2.8)
                    return (
                      <div
                        key={`${subtab}-${item.id}-${idx}`}
                        className={`cv-bar ${selectedIndex === idx ? 'active' : ''}`}
                        style={{ width: `${width}%`, height: `${36 + ((idx * 7) % 24)}px`, background: colors[subtab] }}
                        onClick={() => setSelectedIndex(idx)}
                        title={`${item.label} · ${num(item.duration, 4).toFixed(1)}s`}
                      />
                    )
                  })}
                </div>
                <div className="cv-track-audio">
                  {waves.map((h, idx) => <div key={idx} className="cv-wave" style={{ height: `${h}px` }} />)}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, gap: 10, flexWrap: 'wrap' }}>
                  <span className="cv-label-chip">🎵 {audioName || 'Áudio do job'}</span>
                  {audioUrl ? <audio controls src={audioUrl} style={{ width: 'min(100%, 360px)' }} /> : <span className="cv-muted">Áudio visível apenas nesta sessão se o arquivo já não estiver exposto pelo backend.</span>}
                </div>
              </div>
            </div>

            <div className="cv-editor-meta">
              <div className="cv-card" style={{ padding: 16 }}>
                <div className="cv-card-title">{subtab === 'shotlist' ? 'Shot List Preview' : subtab === 'images' ? 'Imagem selecionada' : 'Vídeo selecionado'}</div>
                <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 12 }}>{selected.label}</div>
                <div className="cv-muted" style={{ marginBottom: 12 }}>Duração: {num(selected.duration, 4).toFixed(2)}s</div>
                <div style={{ display: 'grid', gap: 10 }}>
                  <div>
                    <div className="cv-card-title" style={{ marginBottom: 6 }}>Start Frame</div>
                    <div className="cv-muted">{selected.prompt || 'Sem descrição disponível para este item.'}</div>
                  </div>
                  <div>
                    <div className="cv-card-title" style={{ marginBottom: 6 }}>Action & Camera</div>
                    <div className="cv-muted">{selected.camera} · Mood: {selected.mood}</div>
                  </div>
                  <div>
                    <div className="cv-card-title" style={{ marginBottom: 6 }}>Tipo</div>
                    <span className="cv-pill">{selected.type}</span>
                  </div>
                </div>
              </div>

              <div className="cv-card" style={{ padding: 16 }}>
                <div className="cv-card-title">Itens do editor</div>
                <div className="cv-segment-grid">
                  {currentList.map((item, idx) => (
                    <div className="cv-thumb" key={`${subtab}-thumb-${item.id}-${idx}`} onClick={() => setSelectedIndex(idx)}>
                      <div className="cv-thumb-media">
                        {subtab === 'videos' ? (
                          item.mediaUrl ? <video src={item.mediaUrl} muted /> : null
                        ) : item.mediaUrl ? (
                          <img src={item.mediaUrl} alt={item.label} />
                        ) : null}
                      </div>
                      <div className="cv-thumb-body">
                        <div style={{ fontWeight: 700 }}>{item.label}</div>
                        <div className="cv-muted">{num(item.duration, 4).toFixed(1)}s</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="cv-empty">Ainda não existem itens suficientes para o Editor.</div>
        )}
      </div>
    </div>
  )
}

function FlowTab({ status, audioName }) {
  const concept = status?.creative_concept || {}
  const scenes = (status?.scenes || []).filter(Boolean)
  const videos = (((status?.lipsync_clips || []).some(c => c?.success && c?.video_url) ? status?.lipsync_clips : status?.video_clips) || []).filter(Boolean)
  const referenceUrls = (status?.reference_image_urls || []).map(absUrl).filter(Boolean)
  const characterCards = referenceUrls.length ? referenceUrls.slice(0, 2) : scenes.map(getSceneImage).filter(Boolean).slice(0, 2)
  const planItems = [
    ['Plano', status?.status === 'completed' || status?.progress > 5],
    ['Conceito criativo', !!concept?.directors_vision],
    ['Elenco de personagens', characterCards.length > 0],
    ['Direção criativa', !!concept?.primary_visual_style || !!concept?.texture_atmosphere],
    ['Cinematografia', scenes.length > 0],
    ['Síntese de movimento', videos.length > 0],
    ['Pós-produção', !!status?.merge_url],
  ]
  const colorPalette = Array.isArray(concept?.color_palette) ? concept.color_palette : []
  return (
    <div className="cv-flow">
      <div className="cv-flow-card">
        <div className="cv-flow-title">🧭 Plano</div>
        <div className="cv-segment-grid">
          {planItems.map(([label, ok]) => (
            <div key={label} className="cv-card" style={{ padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <span>{label}</span>
                <span style={{ color: ok ? '#22c55e' : '#64748b' }}>{ok ? '✓' : '•'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">🧠 Memória recuperada</div>
        <div className="cv-note">{status?.description || 'Descrição original do job não disponível na resposta atual, mas o pipeline mantém duração, BPM, tonalidade e estilo para reconstruir o contexto.'}</div>
        <div className="cv-kv" style={{ marginTop: 14 }}>
          <div className="cv-card"><div className="cv-muted">Áudio</div><div className="cv-kv-value">{audioName || 'Faixa atual'}</div></div>
          <div className="cv-card"><div className="cv-muted">BPM</div><div className="cv-kv-value">{status?.audio_bpm || '--'}</div></div>
          <div className="cv-card"><div className="cv-muted">Tom</div><div className="cv-kv-value">{status?.audio_key || '--'}</div></div>
        </div>
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">🎨 Conceito criativo</div>
        <div className="cv-grid cv-grid-2">
          <div className="cv-card" style={{ padding: 16 }}>
            <div className="cv-card-title">Director's Vision</div>
            <div className="cv-muted">{concept?.directors_vision || 'Aguardando conceito criativo.'}</div>
          </div>
          <div className="cv-card" style={{ padding: 16 }}>
            <div className="cv-card-title">Estilo primário</div>
            <div style={{ fontWeight: 800, marginBottom: 10 }}>{concept?.primary_visual_style || status?.config?.style || 'N/D'}</div>
            <div className="cv-muted">{concept?.texture_atmosphere || 'Sem textura/atmosfera detalhada.'}</div>
          </div>
        </div>
        {colorPalette.length > 0 && (
          <div className="cv-swatches">
            {colorPalette.map((hex, idx) => <div key={idx} className="cv-swatch" style={{ background: hex }}>{hex}</div>)}
          </div>
        )}
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">👥 Elenco de personagens</div>
        {characterCards.length ? (
          <div className="cv-mini-grid">
            {characterCards.map((url, idx) => (
              <div key={idx} className="cv-mini-card">
                <img src={url} alt={`Personagem ${idx + 1}`} />
                <div>{idx === 0 ? 'Protagonista / Referência principal' : `Referência complementar ${idx}`}</div>
              </div>
            ))}
          </div>
        ) : <div className="cv-empty">Nenhuma referência visual disponível.</div>}
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">🪄 Direção criativa</div>
        <div className="cv-card" style={{ padding: 16 }}>
          <div className="cv-card-title">Narrativa e direção</div>
          <div className="cv-muted">{concept?.directors_vision || 'Sem narrativa disponível.'}</div>
          <div className="cv-divider" />
          <div className="cv-muted">Textura/atmosfera: {concept?.texture_atmosphere || 'N/D'}</div>
        </div>
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">📸 Cinematografia</div>
        {scenes.length ? (
          <div className="cv-mini-grid">
            {scenes.map((scene, idx) => (
              <div className="cv-mini-card" key={scene.scene_number || idx}>
                {getSceneImage(scene) ? <img src={getSceneImage(scene)} alt={`Cena ${scene.scene_number || idx + 1}`} /> : <div className="cv-empty" style={{ minHeight: 120 }}>Sem imagem</div>}
                <div>Cena {scene.scene_number || idx + 1}</div>
              </div>
            ))}
          </div>
        ) : <div className="cv-empty">As cenas/imagens aparecerão aqui após a geração.</div>}
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">🎞 Síntese de movimento</div>
        {videos.length ? (
          <div className="cv-mini-grid">
            {videos.map((clip, idx) => (
              <div className="cv-mini-card" key={clip.scene_number || idx}>
                {getVideoUrl(clip) ? <video src={getVideoUrl(clip)} muted /> : <div className="cv-empty" style={{ minHeight: 120 }}>Sem vídeo</div>}
                <div>Vídeo {clip.scene_number || idx + 1}</div>
              </div>
            ))}
          </div>
        ) : <div className="cv-empty">Os segmentos de vídeo aparecerão aqui.</div>}
      </div>

      <div className="cv-flow-card">
        <div className="cv-flow-title">🏁 Pós-produção</div>
        {status?.merge_url ? (
          <div className="cv-video-box">
            <video controls src={absUrl(status.merge_url)} />
          </div>
        ) : (
          <div className="cv-empty">O vídeo final aparecerá aqui depois do merge.</div>
        )}
      </div>
    </div>
  )
}

export default function Dashboard({ onBack }) {
  const [upload, setUpload] = useState({
    audio: null,
    description: '',
    style: 'realistic',
    duration: 'full',
    aspect_ratio: '16:9',
    resolution: '720p',
    refs: [null, null, null],
  })
  const [jobId, setJobId] = useState('')
  const [jobStatus, setJobStatus] = useState(null)
  const [activeTab, setActiveTab] = useState('results')
  const [resumeId, setResumeId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [audioObjectUrl, setAudioObjectUrl] = useState('')
  const [audioName, setAudioName] = useState('')
  const pollRef = useRef(null)

  useEffect(() => {
    const savedJob = localStorage.getItem('clipvox_active_job')
    const savedName = localStorage.getItem('clipvox_active_name')
    if (savedJob) {
      setJobId(savedJob)
      if (savedName) setAudioName(savedName)
      fetchStatus(savedJob, true)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const startPolling = (id) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => fetchStatus(id, false), 3500)
  }

  const shouldKeepPolling = (status) => {
    if (!status) return false
    if (status.status === 'processing' || status.status === 'pending') return true
    const sub = [status.videos_status, status.lipsync_status, status.merge_status]
    return sub.some(v => ['processing', 'retrying', 'pending', 'ready'].includes(v))
  }

  const fetchStatus = async (id = jobId, autoPoll = false) => {
    if (!id) return
    try {
      const res = await fetch(`${API_URL}/api/videos/status/${id}`)
      if (!res.ok) throw new Error('Job não encontrado')
      const data = await res.json()
      setJobStatus(data)
      setJobId(id)
      localStorage.setItem('clipvox_active_job', id)
      if (data.audio_filename && !audioName) {
        setAudioName(data.audio_filename)
        localStorage.setItem('clipvox_active_name', data.audio_filename)
      }
      if (shouldKeepPolling(data)) {
        if (autoPoll || !pollRef.current) startPolling(id)
      } else if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch (e) {
      setError(e.message || 'Erro ao consultar job')
    }
  }

  const handleGenerate = async () => {
    if (!upload.audio) {
      setError('Escolha um áudio antes de gerar.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl)
      const nextAudioUrl = URL.createObjectURL(upload.audio)
      setAudioObjectUrl(nextAudioUrl)
      setAudioName(upload.audio.name)
      localStorage.setItem('clipvox_active_name', upload.audio.name)

      const fd = new FormData()
      fd.append('audio', upload.audio)
      fd.append('description', upload.description || '')
      fd.append('style', upload.style)
      fd.append('duration', upload.duration)
      fd.append('aspect_ratio', upload.aspect_ratio)
      fd.append('resolution', upload.resolution)
      upload.refs.forEach((file, idx) => {
        if (file) fd.append(idx === 0 ? 'ref_image' : idx === 1 ? 'ref_image_2' : 'ref_image_3', file)
      })

      const res = await fetch(`${API_URL}/api/videos/generate`, { method: 'POST', body: fd })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || data.message || 'Erro ao iniciar geração')
      setJobId(data.job_id)
      localStorage.setItem('clipvox_active_job', data.job_id)
      saveHistory(data.job_id, upload.audio.name)
      setActiveTab('tela')
      await fetchStatus(data.job_id, true)
    } catch (e) {
      setError(e.message || 'Falha inesperada ao gerar videoclipe')
    } finally {
      setBusy(false)
    }
  }

  const postAction = async (path, formData = null) => {
    if (!jobId) return
    setBusy(true)
    setError('')
    try {
      const res = await fetch(`${API_URL}${path}`, {
        method: 'POST',
        body: formData || undefined,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || data.message || 'Ação falhou')
      await fetchStatus(jobId, true)
      return data
    } catch (e) {
      setError(e.message || 'Erro na ação')
      throw e
    } finally {
      setBusy(false)
    }
  }

  const handleGenerateClips = () => postAction(`/api/videos/generate-clips/${jobId}?mode=std`)
  const handleRunLipSync = () => {
    const fd = new FormData()
    fd.append('model', 'kling')
    return postAction(`/api/videos/lipsync/${jobId}`, fd)
  }
  const handleMerge = () => postAction(`/api/videos/merge/${jobId}`)
  const handleRetryClips = () => postAction(`/api/videos/retry-clips/${jobId}?mode=std`)
  const handleCancel = () => postAction(`/api/videos/cancel/${jobId}`)

  const handleResume = async () => {
    if (!resumeId.trim()) return
    setError('')
    await fetchStatus(resumeId.trim(), true)
    setActiveTab('tela')
  }

  const resetAll = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = null
    localStorage.removeItem('clipvox_active_job')
    localStorage.removeItem('clipvox_active_name')
    setJobId('')
    setJobStatus(null)
    setResumeId('')
    setError('')
    setBusy(false)
    setActiveTab('results')
  }

  const audioUrl = useMemo(() => {
    if (jobStatus?.audio_file_url) return absUrl(jobStatus.audio_file_url)
    return audioObjectUrl || ''
  }, [jobStatus?.audio_file_url, audioObjectUrl])

  return (
    <div className="cv-app">
      <style>{CSS}</style>
      <TopNav onBack={onBack} hasJob={!!jobId} />
      <div className="cv-container">
        <div className="cv-shell">
          <SidebarStatus
            status={jobStatus}
            resumeId={resumeId}
            setResumeId={setResumeId}
            onResume={handleResume}
            onReset={resetAll}
            onCancel={handleCancel}
          />

          <div>
            {!jobId && <UploadPanel state={upload} setState={setUpload} onGenerate={handleGenerate} busy={busy} />}

            {jobId && (
              <div className="cv-main cv-panel">
                <div className="cv-header-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                    <div>
                      <h2 className="cv-section-title">Projeto ativo</h2>
                      <p className="cv-muted">Job ID: {jobId}</p>
                      <div className="cv-pills" style={{ marginTop: 10 }}>
                        <span className="cv-pill">Áudio: {audioName || 'Faixa atual'}</span>
                        <span className="cv-pill">Estilo: {jobStatus?.config?.style || upload.style}</span>
                        <span className="cv-pill">Aspect Ratio: {jobStatus?.config?.aspect_ratio || upload.aspect_ratio}</span>
                        <span className="cv-pill">Resolução: {jobStatus?.config?.resolution || upload.resolution}</span>
                      </div>
                    </div>
                    <div className="cv-note" style={{ maxWidth: 420 }}>
                      O backend já entrega <strong>creative_concept</strong>, <strong>scenes</strong>, <strong>video_clips</strong>, <strong>lipsync_clips</strong> e <strong>merge_url</strong>, o que permite montar as abas Resultados, Editor e Tela sobre o mesmo job. As etapas do pipeline também são persistidas no Supabase. 
                    </div>
                  </div>
                </div>

                <ActionBar
                  status={jobStatus}
                  onGenerateClips={handleGenerateClips}
                  onRunLipSync={handleRunLipSync}
                  onMerge={handleMerge}
                  onRetryClips={handleRetryClips}
                  busy={busy}
                />

                <div className="cv-tabs">
                  <button className={`cv-tab ${activeTab === 'results' ? 'active' : ''}`} onClick={() => setActiveTab('results')}>Resultados</button>
                  <button className={`cv-tab ${activeTab === 'editor' ? 'active' : ''}`} onClick={() => setActiveTab('editor')}>Editor</button>
                  <button className={`cv-tab ${activeTab === 'tela' ? 'active' : ''}`} onClick={() => setActiveTab('tela')}>Tela</button>
                </div>

                {error && <div className="cv-card" style={{ marginBottom: 16, borderColor: 'rgba(239,68,68,.3)', color: '#fecaca' }}>❌ {error}</div>}

                {activeTab === 'results' && <ResultsTab status={jobStatus} jobId={jobId} />}
                {activeTab === 'editor' && <EditorTab status={jobStatus} audioUrl={audioUrl} audioName={audioName} />}
                {activeTab === 'tela' && <FlowTab status={jobStatus} audioName={audioName} />}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
