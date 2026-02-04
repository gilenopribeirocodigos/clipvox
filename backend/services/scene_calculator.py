"""
Calculador cinematográfico de scenes
Determina quantidade e distribuição de cenas baseado em análise musical
"""
import random
from config import (
    SCENE_DURATION_LOW_ENERGY,
    SCENE_DURATION_MID_ENERGY,
    SCENE_DURATION_HIGH_ENERGY,
    MIN_SCENES,
    MAX_SCENES,
    CINEMATIC_DENSITY_FACTOR,
    CAMERA_MOVEMENTS,
    TRANSITIONS
)


def calculate_cinematic_scenes(audio_metadata: dict, user_description: str = "") -> dict:
    """
    Calcula scenes dinamicamente baseado na música
    
    Retorna estrutura completa de scenes com:
    - Número total de scenes
    - Duração de cada scene
    - Posição temporal
    - Energia esperada
    - Camera movement
    - Transition type
    """
    duration = audio_metadata["duration"]
    bpm = audio_metadata["bpm"]
    energy_profile = audio_metadata["energy_profile"]
    structural_segments = audio_metadata.get("structural_segments", [])
    
    # ─── STEP 1: Calcular número base de scenes ──────────────
    # Fórmula: baseado em BPM e duração
    beats_per_second = bpm / 60.0
    total_beats = duration * beats_per_second
    total_measures = total_beats / 4.0  # assume 4/4 time signature
    
    # Densidade cinematográfica: 1.5 a 2.0 scenes por measure
    base_scenes = int(total_measures * CINEMATIC_DENSITY_FACTOR)
    
    # ─── STEP 2: Ajustar pela energia média ──────────────────
    avg_energy = sum(energy_profile) / len(energy_profile) if energy_profile else 0.5
    
    if avg_energy > 0.7:
        # Música de alta energia → mais cortes
        energy_multiplier = 1.3
    elif avg_energy < 0.4:
        # Música calma → menos cortes, cenas mais longas
        energy_multiplier = 0.7
    else:
        energy_multiplier = 1.0
    
    num_scenes = int(base_scenes * energy_multiplier)
    
    # ─── STEP 3: Aplicar limites ─────────────────────────────
    num_scenes = max(MIN_SCENES, min(MAX_SCENES, num_scenes))
    
    # ─── STEP 4: Distribuir scenes ao longo do tempo ─────────
    scenes = []
    time_cursor = 0.0
    
    for i in range(num_scenes):
        # Progresso no vídeo (0.0 a 1.0)
        progress = i / num_scenes
        
        # Qual chunk de energia estamos? (mapeia 0-1 para 0-len(energy_profile))
        energy_index = int(progress * (len(energy_profile) - 1))
        local_energy = energy_profile[energy_index]
        
        # ─── Determinar duração desta scene baseado em energia ───
        if local_energy > 0.7:
            # Alta energia → cenas curtas e rápidas
            scene_duration = SCENE_DURATION_HIGH_ENERGY
        elif local_energy < 0.4:
            # Baixa energia → cenas longas e contemplativas
            scene_duration = SCENE_DURATION_LOW_ENERGY
        else:
            # Energia média
            scene_duration = SCENE_DURATION_MID_ENERGY
        
        # Adicionar variação aleatória ±20% pra não ficar mecânico
        variation = random.uniform(0.8, 1.2)
        scene_duration *= variation
        
        # Garantir que não ultrapassa o final
        if time_cursor + scene_duration > duration:
            scene_duration = duration - time_cursor
        
        # ─── Camera movement (variar pra não repetir) ─────────
        camera_movement = random.choice(CAMERA_MOVEMENTS)
        
        # ─── Transition type ──────────────────────────────────
        # Cut é mais comum (70%), dissolve/fade em momentos específicos
        if i == 0:
            transition = "fade"  # primeira scene sempre fade in
        elif local_energy > 0.8:
            transition = "cut"  # alta energia = cortes secos
        elif i in [int(num_scenes * seg) for seg in structural_segments]:
            # Mudanças estruturais usam dissolve
            transition = "dissolve"
        else:
            # Randomizado com peso
            transition = random.choices(
                TRANSITIONS,
                weights=[70, 20, 8, 2],  # cut 70%, dissolve 20%, fade 8%, wipe 2%
                k=1
            )[0]
        
        # ─── Mood baseado em energia ──────────────────────────
        if local_energy > 0.75:
            mood = random.choice(["energético", "intenso", "vibrante", "explosivo"])
        elif local_energy > 0.5:
            mood = random.choice(["dinâmico", "empolgante", "rítmico"])
        elif local_energy > 0.3:
            mood = random.choice(["contemplativo", "suave", "tranquilo"])
        else:
            mood = random.choice(["íntimo", "sereno", "melancólico", "calmo"])
        
        # ─── Construir objeto da scene ────────────────────────
        scene = {
            "scene_number": i + 1,
            "start_time": round(time_cursor, 2),
            "duration_seconds": round(scene_duration, 2),
            "energy_level": round(local_energy, 2),
            "camera_movement": camera_movement,
            "transition": transition,
            "mood": mood,
            # prompt será gerado depois pelo Claude
            "prompt": ""  
        }
        
        scenes.append(scene)
        time_cursor += scene_duration
        
        # Break se chegou no fim
        if time_cursor >= duration:
            break
    
    # ─── STEP 5: Calcular segments (agrupamentos) ────────────
    # Agrupa scenes em chunks de 5-8 pra processar em batch
    scenes_per_segment = 6
    num_segments = (len(scenes) + scenes_per_segment - 1) // scenes_per_segment
    
    segments = []
    for seg_idx in range(num_segments):
        start_idx = seg_idx * scenes_per_segment
        end_idx = min(start_idx + scenes_per_segment, len(scenes))
        segment_scenes = scenes[start_idx:end_idx]
        
        segments.append({
            "segment_number": seg_idx + 1,
            "scenes": [s["scene_number"] for s in segment_scenes],
            "duration": sum(s["duration_seconds"] for s in segment_scenes)
        })
    
    # ─── RESULT ───────────────────────────────────────────────
    return {
        "total_scenes": len(scenes),
        "total_segments": len(segments),
        "avg_scene_duration": round(duration / len(scenes), 2) if scenes else 0,
        "scenes": scenes,
        "segments": segments,
        "calculation_metadata": {
            "bpm": bpm,
            "duration": duration,
            "avg_energy": round(avg_energy, 2),
            "energy_multiplier": round(energy_multiplier, 2),
            "base_scenes": base_scenes
        }
    }


def get_scene_summary(scene_structure: dict) -> str:
    """Helper pra debug - resumo legível da estrutura"""
    return f"""
📊 Scene Structure Summary:
   Total Scenes: {scene_structure['total_scenes']}
   Total Segments: {scene_structure['total_segments']}
   Avg Scene Duration: {scene_structure['avg_scene_duration']}s
   
   Scene Duration Range: {min(s['duration_seconds'] for s in scene_structure['scenes']):.1f}s - {max(s['duration_seconds'] for s in scene_structure['scenes']):.1f}s
   
   Energy Distribution:
   - High energy scenes (>0.7): {sum(1 for s in scene_structure['scenes'] if s['energy_level'] > 0.7)}
   - Mid energy scenes (0.4-0.7): {sum(1 for s in scene_structure['scenes'] if 0.4 <= s['energy_level'] <= 0.7)}
   - Low energy scenes (<0.4): {sum(1 for s in scene_structure['scenes'] if s['energy_level'] < 0.4)}
"""
