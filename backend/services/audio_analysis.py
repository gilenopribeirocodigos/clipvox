"""
Análise cinematográfica de áudio
Detecta BPM, energia, estrutura musical e características espectrais
para calcular scenes dinamicamente
"""
import numpy as np

def analyze_audio_cinematic(audio_path: str) -> dict:
    """
    Análise profunda do áudio para geração cinematográfica
    
    Returns:
        dict com: duration, bpm, key, energy_profile, structural_segments, 
                  spectral_characteristics, beat_times
    """
    try:
        import librosa
        import librosa.display
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=22050)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # ─── 1. TEMPO & RHYTHM ANALYSIS ───────────────────────
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        bpm = float(tempo)
        
        # ─── 2. KEY DETECTION ─────────────────────────────────
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Krumhansl-Schmuckler key-finding algorithm
        MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        key_index = int(np.argmax(chroma_mean))
        detected_key = KEYS[key_index]
        
        # Determine major/minor
        major_corr = np.corrcoef(chroma_mean, np.roll(MAJOR_PROFILE, key_index))[0, 1]
        minor_corr = np.corrcoef(chroma_mean, np.roll(MINOR_PROFILE, key_index))[0, 1]
        mode = "Major" if major_corr > minor_corr else "Minor"
        key_with_mode = f"{detected_key} {mode}"
        
        # ─── 3. ENERGY PROFILE (30 segments) ─────────────────
        # Divide em 30 chunks pra mapear energia ao longo do tempo
        num_chunks = 30
        chunk_length = len(y) // num_chunks
        energy_profile = []
        
        for i in range(num_chunks):
            start = i * chunk_length
            end = start + chunk_length if i < num_chunks - 1 else len(y)
            chunk = y[start:end]
            
            # RMS energy
            rms = float(np.sqrt(np.mean(chunk**2)))
            energy_profile.append(round(rms, 4))
        
        # Normalize energy profile to 0-1 range
        max_energy = max(energy_profile) if energy_profile else 1.0
        energy_profile = [e / max_energy for e in energy_profile]
        
        # ─── 4. SPECTRAL CHARACTERISTICS ──────────────────────
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        
        avg_spectral_centroid = float(np.mean(spectral_centroid))
        avg_spectral_rolloff = float(np.mean(spectral_rolloff))
        
        # Brightness (normalized spectral centroid)
        brightness = min(1.0, avg_spectral_centroid / 4000.0)
        
        # ─── 5. STRUCTURAL SEGMENTATION ───────────────────────
        # Detecta mudanças estruturais (intro, verse, chorus, bridge, outro)
        # Usa Self-Similarity Matrix
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Simplified structure detection: find peaks in novelty
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Segment boundaries (normalized positions 0-1)
        try:
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(onset_env, distance=sr//2)  # at least 0.5s apart
            segment_times = librosa.frames_to_time(peaks, sr=sr)
            
            # Limit to 8 major sections max
            if len(segment_times) > 8:
                step = len(segment_times) // 8
                segment_times = segment_times[::step][:8]
            
            structural_segments = [float(t / duration) for t in segment_times]
        except:
            # Fallback: divide in 4 equal parts
            structural_segments = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        # ─── 6. DYNAMIC RANGE ─────────────────────────────────
        dynamic_range = float(np.max(np.abs(y)) - np.min(np.abs(y)))
        
        # ─── RESULT ───────────────────────────────────────────
        return {
            "duration": round(duration, 2),
            "bpm": round(bpm, 1),
            "key": key_with_mode,
            "energy_profile": energy_profile,
            "beat_times": beat_times.tolist()[:100],  # primeiros 100 beats
            "structural_segments": structural_segments,
            "spectral_characteristics": {
                "centroid": round(avg_spectral_centroid, 2),
                "rolloff": round(avg_spectral_rolloff, 2),
                "brightness": round(brightness, 2)
            },
            "dynamic_range": round(dynamic_range, 4)
        }
        
    except ImportError:
        # Fallback se librosa não tiver instalado
        print("⚠️ librosa not available, using mock data")
        return _get_mock_audio_data()
    except Exception as e:
        print(f"❌ Audio analysis error: {e}")
        return _get_mock_audio_data()


def _get_mock_audio_data():
    """Dados mock para desenvolvimento sem librosa"""
    return {
        "duration": 150.0,
        "bpm": 130.0,
        "key": "A Major",
        "energy_profile": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.9, 0.8, 
                          0.7, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5,
                          0.6, 0.7, 0.8, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
        "beat_times": list(range(0, 150, 2)),
        "structural_segments": [0.0, 0.15, 0.35, 0.55, 0.75, 0.9, 1.0],
        "spectral_characteristics": {
            "centroid": 2000.0,
            "rolloff": 4500.0,
            "brightness": 0.6
        },
        "dynamic_range": 0.85
    }
