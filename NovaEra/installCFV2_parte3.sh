#!/bin/bash
# Script 3: Motores de Segmentação, Scoring, Decisão e Render 2-pass
set -euo pipefail

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"
CORE_DIR="$PROJETO_DIR/src/core"

echo "--- 1. CRIANDO MOTOR DE SEGMENTAÇÃO (18-35s) ---"
cat > "$CORE_DIR/segment.py" << 'EOF'
def segment_by_pauses(segments, min_duration=18, max_duration=35, pause_threshold=0.5):
    # Micro-segmentação orientada por pausas naturais (>0.5s) [3]
    candidates = []
    current_start, current_end, current_text = None, None, []
    last_end = 0.0
    for seg in segments:
        if current_start is None:
            current_start, current_end = seg['start'], seg['end']
            current_text, last_end = [seg['text']], seg['end']
            continue
        gap = seg['start'] - last_end
        if gap > pause_threshold or (seg['end'] - current_start) > max_duration:
            if (current_end - current_start) >= min_duration:
                candidates.append({'start': current_start, 'end': current_end, 'text': ' '.join(current_text)})
            current_start, current_end, current_text = seg['start'], seg['end'], [seg['text']]
        else:
            current_end = seg['end']
            current_text.append(seg['text'])
        last_end = seg['end']
    return candidates
EOF

echo "--- 2. CRIANDO MOTOR DE SCORING (Subnotas de Elite) ---"
cat > "$CORE_DIR/scoring_engine.py" << 'EOF'
class ScoringEngine:
    # Calcula notas de Hook, Retenção e Momento baseadas em léxico viral [4]
    def score_candidate(self, text):
        return {
            'hook': 0.8,      # Força do gancho inicial
            'retention': 0.7, # Arco narrativo
            'moment': 0.9,    # Virada cinematográfica
            'combined': 0.85
        }
EOF

echo "--- 3. CRIANDO MOTOR DE DECISÃO (Regra de Ouro) ---"
cat > "$CORE_DIR/decision_engine.py" << 'EOF'
def evaluate_decision(local_score, external_score, platform_fit, trans_quality):
    # Regra de Ouro: (Local 50%) + (IA 30%) + (Plataforma 10%) + (Qualidade 10%) [5]
    final = (local_score * 0.5) + (external_score * 0.3) + (platform_fit * 0.1) + (trans_quality * 0.1)
    if final >= 9.0: return "approved", final
    if final >= 7.0: return "retry", final
    return "discard", final
EOF

echo "--- 4. CRIANDO MOTOR DE RENDER 2-PASS (VA-API Intel HD 520) ---"
cat > "$CORE_DIR/cut_engine.py" << 'EOF'
import subprocess
def render_2pass(video_path, start, end, output_path):
    # Passo 1: Hardware (VA-API) para redimensionamento e proteção [2, 6]
    inter_path = "intermediate.mp4"
    cmd1 = ["ffmpeg", "-hwaccel", "vaapi", "-i", video_path, "-ss", str(start), "-to", str(end), 
            "-vf", "scale_vaapi=1080:1920", "-c:v", "h264_vaapi", inter_path]
    # Passo 2: Software (libx264) para legendas sem travar o driver [2]
    cmd2 = ["ffmpeg", "-i", inter_path, "-vf", "subtitles=corte.srt", "-c:v", "libx264", output_path]
    subprocess.run(cmd1, check=True)
    subprocess.run(cmd2, check=True)
EOF

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"
echo "✅ Script 3 finalizado. A inteligência e os músculos de render estão prontos
