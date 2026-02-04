"""
Serviço de geração de conceito criativo com Claude API
Gera Director's Vision, paleta de cores e prompts cinematográficos para cada scene
"""
import json
from config import ANTHROPIC_API_KEY


def generate_creative_concept_with_prompts(
    audio_metadata: dict,
    scene_structure: dict,
    user_description: str,
    style: str = "realistic"
) -> dict:
    """
    Usa Claude API pra gerar:
    1. Director's Vision completo
    2. Paleta de cores
    3. Prompt detalhado pra cada uma das N scenes calculadas
    
    Returns:
        dict com directors_vision, color_palette, texture_atmosphere, 
        e array 'scenes' com prompts preenchidos
    """
    
    if not ANTHROPIC_API_KEY:
        print("⚠️ ANTHROPIC_API_KEY not set, using mock concept")
        return _generate_mock_concept(scene_structure, user_description)
    
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # ─── Prepare context ──────────────────────────────────
        duration = audio_metadata["duration"]
        bpm = audio_metadata["bpm"]
        key = audio_metadata["key"]
        num_scenes = scene_structure["total_scenes"]
        scenes = scene_structure["scenes"]
        
        # Style mapping
        style_descriptors = {
            "realistic": "Photorealistic, cinematic quality, 8K HDR, film grain, natural lighting",
            "cinematic": "Epic cinematic style, anamorphic lens, dramatic lighting, color grading, Blade Runner 2049 aesthetic",
            "animated": "Pixar-style 3D animation, vibrant colors, expressive characters, Studio Ghibli influence",
            "retro": "Retro 80s VHS aesthetic, synthwave colors, grain and artifacts, neon lights"
        }
        visual_style = style_descriptors.get(style, style_descriptors["realistic"])
        
        # ─── Build prompt ─────────────────────────────────────
        prompt = f"""Você é um diretor de videoclipes profissional com expertise em narrativa visual e sincronização musical.

MÚSICA:
- Duração: {duration}s
- BPM: {bpm}
- Tonalidade: {key}
- Estilo Visual Desejado: {visual_style}

DESCRIÇÃO DO ARTISTA:
{user_description or "Videoclipe moderno e impactante"}

ESTRUTURA DE SCENES:
Você deve criar prompts para {num_scenes} cenas que seguem esta estrutura temporal e energética:

{_format_scenes_for_prompt(scenes[:10])}  
... (total de {num_scenes} scenes)

TAREFA:
Gere um conceito criativo COMPLETO em JSON com:

1. **directors_vision** (string): 2-3 parágrafos descrevendo a narrativa visual completa do videoclipe. Deve ser coeso e cinematográfico.

2. **primary_visual_style** (string): Descrição do estilo visual em português

3. **color_palette** (array): 5 cores principais em hex (ex: ["#1a1a2e", "#16213e", ...])

4. **texture_atmosphere** (string): Descrição das texturas e atmosfera em português

5. **scenes** (array): Array com EXATAMENTE {num_scenes} objetos, cada um contendo:
   - scene_number: número da cena (1 a {num_scenes})
   - prompt: prompt DETALHADO em INGLÊS para geração de imagem/vídeo por IA (mínimo 15 palavras, máximo 50 palavras)
   - duration_seconds: {scenes[0]["duration_seconds"]} (já fornecido)
   - camera_movement: "{scenes[0]["camera_movement"]}" (já fornecido)
   - transition: "{scenes[0]["transition"]}" (já fornecido)
   - energy_level: {scenes[0]["energy_level"]} (já fornecido)
   - mood: "{scenes[0]["mood"]}" (já fornecido)

REGRAS PARA OS PROMPTS:
- Cada prompt deve ser ÚNICO e ESPECÍFICO
- Descrever ação, ambiente, iluminação, composição
- Usar linguagem visual cinematográfica
- Sincronizar com o mood e energia da scene
- Variar enquadramentos: wide shot, close-up, medium shot, aerial, etc.
- Incluir detalhes que tornam a cena memorável

FORMATO DE SAÍDA:
Retorne APENAS o JSON, sem markdown, sem explicações. Exemplo:

{{
  "directors_vision": "...",
  "primary_visual_style": "...",
  "color_palette": ["#...", "#...", "#...", "#...", "#..."],
  "texture_atmosphere": "...",
  "scenes": [
    {{
      "scene_number": 1,
      "prompt": "Wide establishing shot of a lone cowboy walking through golden hour desert landscape, dust particles floating in warm sunlight, cinematic composition with rule of thirds, {visual_style}",
      "duration_seconds": 4.5,
      "camera_movement": "dolly in",
      "transition": "fade",
      "energy_level": 0.3,
      "mood": "contemplativo"
    }},
    ...
  ]
}}
"""
        
        # ─── Call Claude API ──────────────────────────────────
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,  # precisa ser grande pra {num_scenes} scenes
            temperature=0.8,  # criatividade moderada
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean potential markdown
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        concept = json.loads(response_text)
        
        # Validar que tem o número certo de scenes
        if len(concept.get("scenes", [])) != num_scenes:
            print(f"⚠️ Claude returned {len(concept.get('scenes', []))} scenes, expected {num_scenes}")
            # Padding ou truncate
            while len(concept["scenes"]) < num_scenes:
                concept["scenes"].append(concept["scenes"][-1])  # duplicate last
            concept["scenes"] = concept["scenes"][:num_scenes]  # truncate
        
        return concept
        
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        return _generate_mock_concept(scene_structure, user_description)


def _format_scenes_for_prompt(scenes: list) -> str:
    """Formata primeiras 10 scenes como exemplo pro Claude"""
    lines = []
    for s in scenes:
        lines.append(
            f"Scene {s['scene_number']}: {s['duration_seconds']}s, "
            f"energy {s['energy_level']}, {s['mood']}, "
            f"camera: {s['camera_movement']}, transition: {s['transition']}"
        )
    return "\n".join(lines)


def _generate_mock_concept(scene_structure: dict, description: str) -> dict:
    """Mock concept quando Claude API não disponível"""
    num_scenes = scene_structure["total_scenes"]
    scenes = scene_structure["scenes"]
    
    # Mock directors vision
    vision = f"""Este videoclipe celebra a energia e autenticidade da cultura brasileira. 
Com {num_scenes} cenas cuidadosamente sincronizadas com a música, navegamos por uma jornada 
visual que alterna entre momentos íntimos e explosões de energia coletiva. 
A cinematografia utiliza movimentos de câmera variados e transições suaves para 
criar um fluxo narrativo orgânico que complementa perfeitamente o ritmo da música."""
    
    # Generate basic prompts
    mock_scenes = []
    for i, scene in enumerate(scenes):
        energy = scene["energy_level"]
        mood = scene["mood"]
        camera = scene["camera_movement"]
        
        # Template baseado em energia
        if energy > 0.7:
            prompt_template = f"Dynamic {camera}, high energy crowd dancing, vibrant colors, dramatic lighting, motion blur, cinematic 8K"
        elif energy > 0.4:
            prompt_template = f"Medium shot with {camera}, people enjoying music, warm atmosphere, golden hour lighting, cinematic composition"
        else:
            prompt_template = f"Intimate {camera}, contemplative mood, soft lighting, shallow depth of field, cinematic framing, peaceful atmosphere"
        
        mock_scenes.append({
            "scene_number": scene["scene_number"],
            "prompt": prompt_template,
            "duration_seconds": scene["duration_seconds"],
            "camera_movement": scene["camera_movement"],
            "transition": scene["transition"],
            "energy_level": scene["energy_level"],
            "mood": scene["mood"]
        })
    
    return {
        "directors_vision": vision,
        "primary_visual_style": "Fotorrealista com iluminação natural",
        "color_palette": ["#8B4513", "#D2691E", "#1E3A5F", "#0052CC", "#F5F5DC"],
        "texture_atmosphere": "Atmosfera autêntica e vibrante com texturas orgânicas",
        "scenes": mock_scenes
    }
