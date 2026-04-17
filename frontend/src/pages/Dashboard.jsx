import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  Handle,
  Position,
  useEdgesState,
  useNodesState,
} from 'reactflow'
import 'reactflow/dist/style.css'

/**
 * CLIPVOX — WORKFLOW VISUAL COM REACT FLOW
 *
 * Objetivo:
 * substituir o encadeamento vertical de PipelineConnector por um canvas visual
 * no estilo FREEBEAT, preservando a identidade do ClipVox.
 *
 * COMO USAR NO SEU PROJETO
 * 1) Instale: npm i reactflow
 * 2) Cole este arquivo no frontend, por exemplo:
 *    src/components/ClipVoxWorkflowFlow.jsx
 * 3) Importe no arquivo principal do ClipVox:
 *    import { ClipVoxWorkflowFlow, clipVoxFlowCss } from './components/ClipVoxWorkflowFlow'
 * 4) Injete o CSS global uma única vez:
 *    <style>{CSS + clipVoxFlowCss}</style>
 * 5) Na aba "Tela", renderize:
 *    <ClipVoxWorkflowFlow
 *      jobId={jobId}
 *      fileName={currentFileName}
 *      jobStatus={jobStatus}
 *      completedClips={completedClips}
 *      lipSyncClips={lipSyncClips}
 *      lipSyncDone={lipSyncDone}
 *      lipSyncUrl={lipSyncUrl}
 *      lipSyncWasStuck={lipSyncWasStuck}
 *      onEditScene={(scene) => setEditModal({ item: scene, type: 'scene' })}
 *      onEditClip={(clip) => handleEditClip(clip)}
 *      onVideosCompleted={handleVideosCompleted}
 *      onLipSyncCompleted={handleLipSyncCompleted}
 *      onRetrySyncClip={handleRetrySyncClip}
 *      onCancel={handleCancel}
 *      onMergeCompleted={(url) => {
 *        setMergeUrlState(url)
 *        setJobStatus(prev => ({ ...prev, merge_url: url, merge_status: 'completed' }))
 *        setActiveTab(0)
 *      }}
 *    />
 *
 * OBSERVAÇÃO IMPORTANTE
 * Este módulo foi feito para encaixar na estrutura que você já usa:
 * creative_concept, scenes, video_clips, videos_status, lipsync_status, merge_status etc.
 * Ele NÃO altera a lógica do backend; só muda a visualização do pipeline.
 */

const API_URL = 'https://clipvox-backend.onrender.com'

export const clipVoxFlowCss = `
  .clipvox-flow-shell {
    background: rgba(16,16,24,.85);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 18px;
    overflow: hidden;
    animation: fadeUp .45s ease;
  }
  .clipvox-flow-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 20px;
    border-bottom: 1px solid rgba(255,255,255,.06);
    background: linear-gradient(180deg, rgba(249,115,22,.05), rgba(255,255,255,0));
  }
  .clipvox-flow-title {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #fff;
  }
  .clipvox-flow-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .5px;
    border: 1px solid rgba(249,115,22,.22);
    background: rgba(249,115,22,.08);
    color: #f97316;
  }
  .clipvox-flow-canvas {
    width: 100%;
    height: 980px;
    background:
      radial-gradient(circle at top, rgba(249,115,22,.05), transparent 22%),
      #0b0b10;
  }
  .clipvox-flow-canvas .react-flow__background path {
    stroke: rgba(255,255,255,.045);
  }
  .clipvox-flow-canvas .react-flow__controls {
    border: 1px solid rgba(255,255,255,.08);
    background: rgba(16,16,24,.92);
    box-shadow: 0 10px 26px rgba(0,0,0,.28);
    border-radius: 14px;
    overflow: hidden;
  }
  .clipvox-flow-canvas .react-flow__controls-button {
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,.06);
    color: #9ca3af;
  }
  .clipvox-flow-canvas .react-flow__controls-button:hover {
    background: rgba(249,115,22,.08);
    color: #fff;
  }
  .clipvox-flow-canvas .react-flow__minimap {
    background: rgba(16,16,24,.95);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    overflow: hidden;
  }
`

const STEP_META = {
  plan: {
    label: 'Plan',
    icon: '🧩',
    title: 'Planejamento',
    subtitle: 'Etapas previstas do job',
    x: 180,
    y: 70,
    w: 320,
  },
  analyzing: {
    label: 'Input Analyzing',
    icon: '🔎',
    title: 'Input Analyzing',
    subtitle: 'Arquivo de áudio analisado',
    x: 180,
    y: 320,
    w: 360,
  },
  creative: {
    label: 'Creative Concept',
    icon: '💡',
    title: 'Creative Concept',
    subtitle: 'Conceito e direção criativa',
    x: 180,
    y: 590,
    w: 520,
  },
  scenes: {
    label: 'Scenes',
    icon: '🖼️',
    title: 'Scenes',
    subtitle: 'Imagens geradas',
    x: 780,
    y: 70,
    w: 700,
  },
  segments: {
    label: 'Video Segments',
    icon: '🎬',
    title: 'Video Segments',
    subtitle: 'Clipes gerados',
    x: 780,
    y: 420,
    w: 700,
  },
  lipsync: {
    label: 'Lip Sync',
    icon: '🎤',
    title: 'Lip Sync',
    subtitle: 'Sincronização vocal',
    x: 1560,
    y: 420,
    w: 520,
  },
  merge: {
    label: 'Merge Video Segments',
    icon: '🧷',
    title: 'Merge Video Segments',
    subtitle: 'Vídeo final',
    x: 1300,
    y: 790,
    w: 620,
  },
}

function getStepState(jobStatus, key, lipSyncDone, lipSyncWasStuck) {
  if (!jobStatus) {
    return { done: false, active: false, pending: true }
  }

  const current = jobStatus.current_step

  const doneMap = {
    plan: !!jobStatus?.creative_concept || ['analyzing', 'creative', 'scenes', 'segments', 'merge'].includes(current),
    analyzing: !!jobStatus?.creative_concept || ['creative', 'scenes', 'segments', 'merge'].includes(current),
    creative: !!jobStatus?.creative_concept,
    scenes: !!jobStatus?.scenes?.length && jobStatus.scenes.some((s) => s.image_url),
    segments: jobStatus?.videos_status === 'completed',
    lipsync: !!lipSyncDone,
    merge: jobStatus?.merge_status === 'completed',
  }

  const activeMap = {
    plan: current === 'plan',
    analyzing: current === 'analyzing',
    creative: current === 'creative',
    scenes: current === 'scenes',
    segments: jobStatus?.videos_status === 'processing' || jobStatus?.videos_status === 'retrying',
    lipsync: jobStatus?.lipsync_status === 'processing' || (!!lipSyncWasStuck && !lipSyncDone),
    merge: jobStatus?.merge_status === 'processing',
  }

  const done = !!doneMap[key]
  const active = !!activeMap[key]
  return { done, active, pending: !done && !active }
}

function edgeStyleFromState(sourceState) {
  if (sourceState.done) {
    return {
      stroke: '#22c55e',
      strokeWidth: 3,
      opacity: 0.95,
    }
  }

  if (sourceState.active) {
    return {
      stroke: '#f97316',
      strokeWidth: 3,
      opacity: 0.95,
      strokeDasharray: '8 8',
    }
  }

  return {
    stroke: '#374151',
    strokeWidth: 2,
    opacity: 0.9,
    strokeDasharray: '5 7',
  }
}

function formatAudioDuration(seconds) {
  if (!seconds && seconds !== 0) return '...'
  const m = Math.floor(seconds / 60)
  const s = String(Math.floor(seconds % 60)).padStart(2, '0')
  return `${m}:${s}`
}

function resolvePrompt(item) {
  return (
    item?.prompt ||
    item?.prompt_used ||
    item?.image_prompt ||
    item?.visual_description ||
    item?.scene_description ||
    item?.scene_prompt ||
    item?.description ||
    ''
  )
}

function statusTone({ done, active }) {
  if (done) {
    return {
      border: 'rgba(34,197,94,.30)',
      bg: 'linear-gradient(180deg, rgba(34,197,94,.10), rgba(16,16,24,.92))',
      shadow: '0 0 0 1px rgba(34,197,94,.08), 0 18px 40px rgba(0,0,0,.28)',
      dot: '#22c55e',
      pillBg: 'rgba(34,197,94,.12)',
      pillColor: '#22c55e',
    }
  }

  if (active) {
    return {
      border: 'rgba(249,115,22,.36)',
      bg: 'linear-gradient(180deg, rgba(249,115,22,.12), rgba(16,16,24,.92))',
      shadow: '0 0 0 1px rgba(249,115,22,.10), 0 18px 40px rgba(0,0,0,.30)',
      dot: '#f97316',
      pillBg: 'rgba(249,115,22,.12)',
      pillColor: '#f97316',
    }
  }

  return {
    border: 'rgba(255,255,255,.08)',
    bg: 'linear-gradient(180deg, rgba(255,255,255,.03), rgba(16,16,24,.92))',
    shadow: '0 14px 34px rgba(0,0,0,.24)',
    dot: '#4b5563',
    pillBg: 'rgba(255,255,255,.05)',
    pillColor: '#6b7280',
  }
}

const nodeBase = {
  borderRadius: 18,
  padding: 14,
  color: '#fff',
  fontFamily: 'DM Sans, sans-serif',
  minHeight: 120,
}

const FlowNode = memo(({ data }) => {
  const tone = statusTone(data.state)

  return (
    <div
      style={{
        ...nodeBase,
        width: data.width || 320,
        border: `1px solid ${tone.border}`,
        background: tone.bg,
        boxShadow: tone.shadow,
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 12,
              display: 'grid',
              placeItems: 'center',
              background: 'rgba(255,255,255,.05)',
              border: '1px solid rgba(255,255,255,.08)',
              fontSize: 16,
              flexShrink: 0,
            }}
          >
            {data.icon}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{data.title}</div>
            <div style={{ color: '#6b7280', fontSize: 11, marginTop: 2 }}>{data.subtitle}</div>
          </div>
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 10px',
            borderRadius: 999,
            background: tone.pillBg,
            color: tone.pillColor,
            border: `1px solid ${tone.border}`,
            fontSize: 10,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: tone.dot,
              boxShadow: data.state.active ? `0 0 12px ${tone.dot}` : 'none',
              animation: data.state.active ? 'pulse 1.4s ease infinite' : 'none',
            }}
          />
          {data.state.done ? 'CONCLUÍDO' : data.state.active ? 'PROCESSANDO' : 'PENDENTE'}
        </div>
      </div>

      {typeof data.render === 'function' ? data.render(data) : null}
    </div>
  )
})

function StepListNodeContent({ jobStatus }) {
  const steps = [
    { id: 'plan', label: 'Plan' },
    { id: 'analyzing', label: 'Input Analyzing' },
    { id: 'creative', label: 'Creative Concept' },
    { id: 'scenes', label: 'Scenes' },
    { id: 'segments', label: 'Video Segments' },
    { id: 'merge', label: 'Merge Video Segments' },
  ]

  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {steps.map((step, index) => {
        const current = jobStatus?.current_step === step.id
        const done =
          step.id === 'plan'
            ? !!jobStatus?.creative_concept
            : step.id === 'analyzing'
              ? !!jobStatus?.creative_concept
              : step.id === 'creative'
                ? !!jobStatus?.creative_concept
                : step.id === 'scenes'
                  ? !!jobStatus?.scenes?.some((s) => s.image_url)
                  : step.id === 'segments'
                    ? jobStatus?.videos_status === 'completed'
                    : jobStatus?.merge_status === 'completed'

        return (
          <div
            key={step.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '9px 10px',
              borderRadius: 12,
              background: 'rgba(255,255,255,.03)',
              border: '1px solid rgba(255,255,255,.06)',
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                background: done ? 'rgba(34,197,94,.15)' : current ? 'rgba(249,115,22,.15)' : 'rgba(255,255,255,.04)',
                border: done ? '1px solid rgba(34,197,94,.35)' : current ? '1px solid rgba(249,115,22,.35)' : '1px solid rgba(255,255,255,.08)',
                color: done ? '#22c55e' : current ? '#f97316' : '#6b7280',
                fontSize: 10,
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {done ? '✓' : index + 1}
            </div>
            <div style={{ flex: 1, fontSize: 12, color: current ? '#fff' : '#9ca3af', fontWeight: current ? 700 : 500 }}>{step.label}</div>
          </div>
        )
      })}
    </div>
  )
}

function InputNodeContent({ fileName, jobStatus }) {
  return (
    <div style={{ display: 'grid', gap: 10 }}>
      <div
        style={{
          background: 'rgba(255,255,255,.04)',
          border: '1px solid rgba(255,255,255,.06)',
          borderRadius: 14,
          padding: 12,
        }}
      >
        <div style={{ color: '#6b7280', fontSize: 10, fontWeight: 700, letterSpacing: .5, marginBottom: 6 }}>INFORMAÇÕES MUSICAIS</div>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{fileName || 'Arquivo atual'}</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', color: '#9ca3af', fontSize: 11 }}>
          <span>⏱ {formatAudioDuration(jobStatus?.audio_duration)}</span>
          {jobStatus?.audio_bpm ? <span>🥁 {Math.round(jobStatus.audio_bpm)} BPM</span> : null}
          {jobStatus?.resolution ? <span>🎥 {jobStatus.resolution}</span> : null}
          {jobStatus?.aspect_ratio ? <span>📐 {jobStatus.aspect_ratio}</span> : null}
        </div>
      </div>
    </div>
  )
}

function CreativeNodeContent({ concept }) {
  if (!concept) {
    return <div style={{ color: '#6b7280', fontSize: 12 }}>Conceito criativo ainda não gerado.</div>
  }

  const blocks = [
    { label: 'Concept Title', value: concept?.title || concept?.concept_title },
    { label: 'Logline', value: concept?.logline },
    { label: "Director's Vision", value: concept?.directors_vision || concept?.director_vision },
    { label: 'Primary Visual Style', value: concept?.primary_visual_style || concept?.visual_style },
  ].filter((b) => !!b.value)

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {blocks.slice(0, 4).map((block) => (
        <div
          key={block.label}
          style={{
            background: 'rgba(255,255,255,.04)',
            border: '1px solid rgba(255,255,255,.06)',
            borderRadius: 14,
            padding: 12,
          }}
        >
          <div style={{ color: '#9ca3af', fontSize: 10, fontWeight: 700, marginBottom: 6 }}>{block.label}</div>
          <div style={{ color: '#fff', fontSize: 12, lineHeight: 1.6 }}>{block.value}</div>
        </div>
      ))}
    </div>
  )
}

function ThumbnailStrip({ items = [], type = 'image', onClickItem }) {
  if (!items.length) {
    return <div style={{ color: '#6b7280', fontSize: 12 }}>Aguardando conteúdo desta etapa.</div>
  }

  const visible = items.slice(0, 20)

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 10 }}>
        {visible.map((item, idx) => {
          const imageUrl = item?.image_url
          const videoUrl = item?.video_url
          const number = item?.scene_number || idx + 1
          const bad = type === 'video' && (!item?.success || !videoUrl)
          const clickable = typeof onClickItem === 'function'

          return (
            <button
              key={`${type}-${number}-${idx}`}
              type="button"
              onClick={() => clickable && onClickItem(item)}
              style={{
                textAlign: 'left',
                borderRadius: 12,
                overflow: 'hidden',
                border: bad ? '1px solid rgba(239,68,68,.25)' : '1px solid rgba(255,255,255,.06)',
                background: 'rgba(255,255,255,.03)',
                padding: 0,
                cursor: clickable ? 'pointer' : 'default',
              }}
            >
              <div style={{ height: 92, background: '#0a0a0e', position: 'relative', display: 'grid', placeItems: 'center' }}>
                {type === 'image' && imageUrl ? (
                  <img src={imageUrl} alt={`scene-${number}`} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                ) : type === 'video' && videoUrl ? (
                  <video src={videoUrl} muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                ) : (
                  <span style={{ fontSize: 24 }}>{bad ? '❌' : type === 'image' ? '🖼️' : '🎬'}</span>
                )}

                <div
                  style={{
                    position: 'absolute',
                    top: 6,
                    left: 6,
                    padding: '2px 6px',
                    borderRadius: 999,
                    background: 'rgba(0,0,0,.65)',
                    color: '#fff',
                    fontSize: 9,
                    fontWeight: 700,
                  }}
                >
                  {type === 'image' ? `Cena ${number}` : `Vídeo ${number}`}
                </div>

                {type === 'video' && !bad ? (
                  <div
                    style={{
                      position: 'absolute',
                      width: 34,
                      height: 34,
                      borderRadius: '50%',
                      display: 'grid',
                      placeItems: 'center',
                      background: 'rgba(249,115,22,.86)',
                      color: '#fff',
                      fontSize: 12,
                    }}
                  >
                    ▶
                  </div>
                ) : null}
              </div>
              <div style={{ padding: 8 }}>
                <div style={{ color: bad ? '#ef4444' : '#fff', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {type === 'image' ? resolvePrompt(item) || 'Cena gerada' : bad ? item?.error || 'Falhou' : resolvePrompt(item) || 'Segmento gerado'}
                </div>
              </div>
            </button>
          )
        })}
      </div>
      {items.length > visible.length ? (
        <div style={{ marginTop: 10, color: '#6b7280', fontSize: 11 }}>Role para ver mais · exibindo {visible.length} de {items.length}</div>
      ) : null}
    </div>
  )
}

function MergePreviewNodeContent({ mergeUrl, mergeStatus, onGenerateMerge, canMerge }) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div
        style={{
          background: 'rgba(255,255,255,.04)',
          border: '1px solid rgba(255,255,255,.06)',
          borderRadius: 14,
          overflow: 'hidden',
          minHeight: 250,
        }}
      >
        {mergeUrl ? (
          <video src={mergeUrl} controls playsInline style={{ width: '100%', display: 'block', background: '#000' }} />
        ) : (
          <div style={{ minHeight: 250, display: 'grid', placeItems: 'center', color: '#6b7280', fontSize: 13 }}>
            {mergeStatus === 'processing' ? 'Mesclando vídeo final...' : 'Prévia do vídeo final aparecerá aqui'}
          </div>
        )}
      </div>

      {!mergeUrl ? (
        <button
          type="button"
          onClick={onGenerateMerge}
          disabled={!canMerge || mergeStatus === 'processing'}
          style={{
            width: '100%',
            padding: '12px 14px',
            borderRadius: 12,
            border: 'none',
            background: canMerge ? 'linear-gradient(135deg,#f97316,#ea580c)' : 'rgba(60,60,70,.55)',
            color: '#fff',
            fontWeight: 700,
            cursor: canMerge ? 'pointer' : 'not-allowed',
            boxShadow: canMerge ? '0 10px 24px rgba(249,115,22,.22)' : 'none',
          }}
        >
          {mergeStatus === 'processing' ? '⏳ Fazendo merge...' : '🧷 Gerar vídeo final'}
        </button>
      ) : null}
    </div>
  )
}

function buildNodes({
  fileName,
  jobStatus,
  completedClips,
  lipSyncClips,
  lipSyncDone,
  lipSyncWasStuck,
  lipSyncUrl,
  mergeUrl,
  onEditScene,
  onEditClip,
  onGenerateMerge,
}) {
  const states = {
    plan: getStepState(jobStatus, 'plan', lipSyncDone, lipSyncWasStuck),
    analyzing: getStepState(jobStatus, 'analyzing', lipSyncDone, lipSyncWasStuck),
    creative: getStepState(jobStatus, 'creative', lipSyncDone, lipSyncWasStuck),
    scenes: getStepState(jobStatus, 'scenes', lipSyncDone, lipSyncWasStuck),
    segments: getStepState(jobStatus, 'segments', lipSyncDone, lipSyncWasStuck),
    lipsync: getStepState(jobStatus, 'lipsync', lipSyncDone, lipSyncWasStuck),
    merge: getStepState(jobStatus, 'merge', lipSyncDone, lipSyncWasStuck),
  }

  return [
    {
      id: 'plan',
      type: 'clipvoxNode',
      position: { x: STEP_META.plan.x, y: STEP_META.plan.y },
      data: {
        ...STEP_META.plan,
        width: STEP_META.plan.w,
        state: states.plan,
        render: () => <StepListNodeContent jobStatus={jobStatus} />,
      },
      draggable: false,
    },
    {
      id: 'analyzing',
      type: 'clipvoxNode',
      position: { x: STEP_META.analyzing.x, y: STEP_META.analyzing.y },
      data: {
        ...STEP_META.analyzing,
        width: STEP_META.analyzing.w,
        state: states.analyzing,
        render: () => <InputNodeContent fileName={fileName} jobStatus={jobStatus} />,
      },
      draggable: false,
    },
    {
      id: 'creative',
      type: 'clipvoxNode',
      position: { x: STEP_META.creative.x, y: STEP_META.creative.y },
      data: {
        ...STEP_META.creative,
        width: STEP_META.creative.w,
        state: states.creative,
        render: () => <CreativeNodeContent concept={jobStatus?.creative_concept} />,
      },
      draggable: false,
    },
    {
      id: 'scenes',
      type: 'clipvoxNode',
      position: { x: STEP_META.scenes.x, y: STEP_META.scenes.y },
      data: {
        ...STEP_META.scenes,
        width: STEP_META.scenes.w,
        state: states.scenes,
        render: () => <ThumbnailStrip items={jobStatus?.scenes || []} type="image" onClickItem={onEditScene} />,
      },
      draggable: false,
    },
    {
      id: 'segments',
      type: 'clipvoxNode',
      position: { x: STEP_META.segments.x, y: STEP_META.segments.y },
      data: {
        ...STEP_META.segments,
        width: STEP_META.segments.w,
        state: states.segments,
        render: () => <ThumbnailStrip items={completedClips || jobStatus?.video_clips || []} type="video" onClickItem={onEditClip} />,
      },
      draggable: false,
    },
    {
      id: 'lipsync',
      type: 'clipvoxNode',
      position: { x: STEP_META.lipsync.x, y: STEP_META.lipsync.y },
      data: {
        ...STEP_META.lipsync,
        width: STEP_META.lipsync.w,
        state: states.lipsync,
        render: () => (
          <div style={{ display: 'grid', gap: 10 }}>
            <div
              style={{
                background: 'rgba(255,255,255,.04)',
                border: '1px solid rgba(255,255,255,.06)',
                borderRadius: 14,
                padding: 12,
              }}
            >
              <div style={{ color: '#9ca3af', fontSize: 10, fontWeight: 700, marginBottom: 6 }}>STATUS</div>
              <div style={{ color: '#fff', fontSize: 12, lineHeight: 1.6 }}>
                {lipSyncDone
                  ? 'Lip sync concluído.'
                  : jobStatus?.lipsync_status === 'processing'
                    ? 'Sincronização em andamento.'
                    : lipSyncWasStuck
                      ? 'Lip sync interrompido. Aguardando retomada.'
                      : 'Etapa pronta para iniciar quando os segmentos estiverem concluídos.'}
              </div>
            </div>
            {lipSyncClips?.length ? <ThumbnailStrip items={lipSyncClips} type="video" /> : null}
            {lipSyncUrl ? (
              <a
                href={lipSyncUrl}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#a78bfa', fontSize: 12, textDecoration: 'none', fontWeight: 700 }}
              >
                🎤 Abrir vídeo sincronizado
              </a>
            ) : null}
          </div>
        ),
      },
      draggable: false,
      hidden: !(completedClips?.some((c) => c?.success) || lipSyncWasStuck || lipSyncDone),
    },
    {
      id: 'merge',
      type: 'clipvoxNode',
      position: { x: STEP_META.merge.x, y: STEP_META.merge.y },
      data: {
        ...STEP_META.merge,
        width: STEP_META.merge.w,
        state: states.merge,
        render: () => (
          <MergePreviewNodeContent
            mergeUrl={mergeUrl || jobStatus?.merge_url}
            mergeStatus={jobStatus?.merge_status}
            onGenerateMerge={onGenerateMerge}
            canMerge={!!completedClips?.some((c) => c?.success) && !!lipSyncDone}
          />
        ),
      },
      draggable: false,
      hidden: !(completedClips?.some((c) => c?.success) && !!lipSyncDone),
    },
  ].filter((node) => !node.hidden)
}

function buildEdges({ jobStatus, lipSyncDone, lipSyncWasStuck, completedClips }) {
  const statePlan = getStepState(jobStatus, 'plan', lipSyncDone, lipSyncWasStuck)
  const stateAnalyzing = getStepState(jobStatus, 'analyzing', lipSyncDone, lipSyncWasStuck)
  const stateCreative = getStepState(jobStatus, 'creative', lipSyncDone, lipSyncWasStuck)
  const stateScenes = getStepState(jobStatus, 'scenes', lipSyncDone, lipSyncWasStuck)
  const stateSegments = getStepState(jobStatus, 'segments', lipSyncDone, lipSyncWasStuck)
  const stateLipsync = getStepState(jobStatus, 'lipsync', lipSyncDone, lipSyncWasStuck)

  const edges = [
    {
      id: 'plan-analyzing',
      source: 'plan',
      target: 'analyzing',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(statePlan).stroke },
      style: edgeStyleFromState(statePlan),
      animated: statePlan.active,
    },
    {
      id: 'analyzing-creative',
      source: 'analyzing',
      target: 'creative',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(stateAnalyzing).stroke },
      style: edgeStyleFromState(stateAnalyzing),
      animated: stateAnalyzing.active,
    },
    {
      id: 'creative-scenes',
      source: 'creative',
      target: 'scenes',
      type: 'smoothstep',
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(stateCreative).stroke },
      style: edgeStyleFromState(stateCreative),
      animated: stateCreative.active,
    },
    {
      id: 'scenes-segments',
      source: 'scenes',
      target: 'segments',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(stateScenes).stroke },
      style: edgeStyleFromState(stateScenes),
      animated: stateScenes.active,
    },
  ]

  if (completedClips?.some((c) => c?.success) || lipSyncWasStuck || lipSyncDone) {
    edges.push({
      id: 'segments-lipsync',
      source: 'segments',
      target: 'lipsync',
      type: 'smoothstep',
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(stateSegments).stroke },
      style: edgeStyleFromState(stateSegments),
      animated: stateSegments.active,
    })
  }

  if (completedClips?.some((c) => c?.success) && lipSyncDone) {
    edges.push({
      id: 'lipsync-merge',
      source: 'lipsync',
      target: 'merge',
      type: 'smoothstep',
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyleFromState(stateLipsync).stroke },
      style: edgeStyleFromState(stateLipsync),
      animated: stateLipsync.active,
    })
  }

  return edges
}

function fitViewOptions() {
  return {
    padding: 0.18,
    includeHiddenNodes: false,
    minZoom: 0.45,
    maxZoom: 1.35,
  }
}

const nodeTypes = {
  clipvoxNode: FlowNode,
}

function ClipVoxWorkflowFlowInner({
  jobId,
  fileName,
  jobStatus,
  completedClips,
  lipSyncClips,
  lipSyncDone,
  lipSyncUrl,
  lipSyncWasStuck,
  onEditScene,
  onEditClip,
  onVideosCompleted,
  onLipSyncCompleted,
  onRetrySyncClip,
  onCancel,
  onMergeCompleted,
}) {
  const [mergeUrl, setMergeUrl] = useState(jobStatus?.merge_url || null)
  const [mergeBusy, setMergeBusy] = useState(false)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const flowRef = useRef(null)

  useEffect(() => {
    setMergeUrl(jobStatus?.merge_url || null)
  }, [jobStatus?.merge_url])

  const handleGenerateMerge = useCallback(async () => {
    if (!jobId || mergeBusy || !completedClips?.some((c) => c?.success) || !lipSyncDone) return

    setMergeBusy(true)
    try {
      const res = await fetch(`${API_URL}/api/videos/merge/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_lipsync: true }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.detail || `Erro ${res.status}`)
      }

      let tries = 0
      const maxTries = 90
      const interval = setInterval(async () => {
        tries += 1
        try {
          const statusRes = await fetch(`${API_URL}/api/videos/status/${jobId}`)
          const status = await statusRes.json()

          if (status?.merge_status === 'completed' && status?.merge_url) {
            clearInterval(interval)
            setMergeUrl(status.merge_url)
            setMergeBusy(false)
            onMergeCompleted?.(status.merge_url)
          }

          if (status?.merge_status === 'failed' || tries >= maxTries) {
            clearInterval(interval)
            setMergeBusy(false)
          }
        } catch {
          if (tries >= maxTries) {
            clearInterval(interval)
            setMergeBusy(false)
          }
        }
      }, 3000)
    } catch (error) {
      console.error('Erro no merge:', error)
      setMergeBusy(false)
    }
  }, [jobId, mergeBusy, completedClips, lipSyncDone, onMergeCompleted])

  const computedNodes = useMemo(
    () =>
      buildNodes({
        fileName,
        jobStatus,
        completedClips,
        lipSyncClips,
        lipSyncDone,
        lipSyncWasStuck,
        lipSyncUrl,
        mergeUrl,
        onEditScene,
        onEditClip,
        onGenerateMerge: handleGenerateMerge,
      }),
    [
      fileName,
      jobStatus,
      completedClips,
      lipSyncClips,
      lipSyncDone,
      lipSyncWasStuck,
      lipSyncUrl,
      mergeUrl,
      onEditScene,
      onEditClip,
      handleGenerateMerge,
    ]
  )

  const computedEdges = useMemo(
    () => buildEdges({ jobStatus, lipSyncDone, lipSyncWasStuck, completedClips }),
    [jobStatus, lipSyncDone, lipSyncWasStuck, completedClips]
  )

  useEffect(() => {
    setNodes(computedNodes)
    setEdges(computedEdges)
  }, [computedNodes, computedEdges, setNodes, setEdges])

  const onInit = useCallback((instance) => {
    flowRef.current = instance
    setTimeout(() => instance.fitView(fitViewOptions()), 50)
  }, [])

  useEffect(() => {
    if (!flowRef.current) return
    const t = setTimeout(() => flowRef.current?.fitView(fitViewOptions()), 60)
    return () => clearTimeout(t)
  }, [nodes, edges])

  const summaryText = useMemo(() => {
    if (!jobStatus) return 'Aguardando status do job.'
    if (jobStatus?.merge_status === 'completed') return 'Pipeline concluído com vídeo final disponível.'
    if (jobStatus?.merge_status === 'processing') return 'Vídeo final em processamento.'
    if (jobStatus?.lipsync_status === 'processing') return 'Lip sync em andamento.'
    if (jobStatus?.videos_status === 'processing' || jobStatus?.videos_status === 'retrying') return 'Gerando segmentos de vídeo.'
    if (jobStatus?.current_step === 'scenes') return 'Gerando cenas.'
    if (jobStatus?.creative_concept) return 'Conceito criativo gerado e pronto para avançar.'
    return 'Workflow inicializado.'
  }, [jobStatus])

  return (
    <div className="clipvox-flow-shell">
      <div className="clipvox-flow-header">
        <div className="clipvox-flow-title">
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 14,
              display: 'grid',
              placeItems: 'center',
              background: 'rgba(249,115,22,.12)',
              border: '1px solid rgba(249,115,22,.22)',
              fontSize: 18,
            }}
          >
            🧠
          </div>
          <div>
            <div style={{ color: '#fff', fontWeight: 800, fontSize: 16 }}>Workflow Visual do ClipVox</div>
            <div style={{ color: '#6b7280', fontSize: 12, marginTop: 2 }}>{summaryText}</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div className="clipvox-flow-badge">📄 {fileName || 'Sem nome'}</div>
          {jobStatus?.current_step ? <div className="clipvox-flow-badge">⚙️ {jobStatus.current_step}</div> : null}
          {jobStatus?.status === 'failed' ? (
            <div style={{ ...badgeError }}>❌ Falha</div>
          ) : jobStatus?.merge_status === 'completed' ? (
            <div style={{ ...badgeSuccess }}>✅ Finalizado</div>
          ) : (
            <div className="clipvox-flow-badge">🟠 Em andamento</div>
          )}
        </div>
      </div>

      <div className="clipvox-flow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          zoomOnDoubleClick={false}
          panOnDrag
          proOptions={{ hideAttribution: true }}
          onInit={onInit}
          fitView
          fitViewOptions={fitViewOptions()}
          defaultViewport={{ x: 0, y: 0, zoom: 0.62 }}
        >
          <Background gap={20} size={1} color="rgba(255,255,255,.05)" />
          <MiniMap
            pannable
            zoomable
            maskColor="rgba(0,0,0,.35)"
            nodeStrokeColor={(n) => n?.data?.state?.done ? '#22c55e' : n?.data?.state?.active ? '#f97316' : '#374151'}
            nodeColor={(n) => n?.data?.state?.done ? 'rgba(34,197,94,.35)' : n?.data?.state?.active ? 'rgba(249,115,22,.35)' : 'rgba(75,85,99,.35)'}
          />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  )
}

const badgeSuccess = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 12px',
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '.5px',
  border: '1px solid rgba(34,197,94,.22)',
  background: 'rgba(34,197,94,.08)',
  color: '#22c55e',
}

const badgeError = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 12px',
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '.5px',
  border: '1px solid rgba(239,68,68,.22)',
  background: 'rgba(239,68,68,.08)',
  color: '#ef4444',
}

export function ClipVoxWorkflowFlow(props) {
  return (
    <ReactFlowProvider>
      <ClipVoxWorkflowFlowInner {...props} />
    </ReactFlowProvider>
  )
}

/**
 * EXEMPLO DE USO DENTRO DA ABA "TELA"
 *
 * Substitua o bloco antigo baseado em PipelineConnector por algo assim:
 *
 * {activeTab === 1 && (
 *   <ClipVoxWorkflowFlow
 *     jobId={jobId}
 *     fileName={currentFileName}
 *     jobStatus={jobStatus}
 *     completedClips={completedClips}
 *     lipSyncClips={lipSyncClips}
 *     lipSyncDone={lipSyncDone}
 *     lipSyncUrl={lipSyncUrl}
 *     lipSyncWasStuck={lipSyncWasStuck}
 *     onEditScene={(scene) => setEditModal({ item: scene, type: 'scene' })}
 *     onEditClip={handleEditClip}
 *     onVideosCompleted={handleVideosCompleted}
 *     onLipSyncCompleted={handleLipSyncCompleted}
 *     onRetrySyncClip={handleRetrySyncClip}
 *     onCancel={handleCancel}
 *     onMergeCompleted={(url) => {
 *       setMergeUrlState(url)
 *       setJobStatus(prev => ({ ...prev, merge_url: url, merge_status: 'completed' }))
 *       setActiveTab(0)
 *     }}
 *   />
 * )}
 *
 * Se quiser manter a aba Resultados intacta, deixe tudo como está.
 * A mudança fica só na aba Tela.
 */
