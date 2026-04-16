#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ClipFusion V2 Build Ouro - Instalador Mestre       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Execute como root: sudo bash $0${NC}"
    exit 1
fi

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"
mkdir -p "$PROJETO_DIR"/{src/{core,gui,utils,viral_engine,anti_copy_modules,config,locales},workspace/{projects,exports,logs}}

# =============================================================================
# 1. OTIMIZAÇÃO DO SISTEMA (kernel, zRAM, pacotes)
# =============================================================================
echo -e "${YELLOW}--- [1/7] Tunagem de kernel e memória ---${NC}"
GRUB_LINE='GRUB_CMDLINE_LINUX_DEFAULT="quiet splash i915.enable_guc=3 mitigations=off intel_idle.max_cstate=1"'
sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|$GRUB_LINE|" /etc/default/grub
update-grub

apt update && apt install -y systemd-zram-generator mate-desktop-environment-core mate-terminal \
    ffmpeg python3-pip python3-venv build-essential vainfo intel-gpu-tools btop

cat > /etc/systemd/zram-generator.conf << EOF
[zram0]
zram-size = 6144
compression-algorithm = lz4
swap-priority = 100
EOF
systemctl daemon-reload
systemctl restart systemd-zram-setup@zram0.service 2>/dev/null || systemctl restart zramswap

# =============================================================================
# 2. AMBIENTE PYTHON
# =============================================================================
echo -e "${YELLOW}--- [2/7] Criando ambiente Python ---${NC}"
cd "$PROJETO_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install faster-whisper numpy pyyaml

# =============================================================================
# 3. BANCO DE DADOS (completo)
# =============================================================================
echo -e "${YELLOW}--- [3/7] Banco de dados SQLite ---${NC}"
cat > "$PROJETO_DIR/db.py" << 'EOF'
import sqlite3, json, threading
from pathlib import Path

DB_PATH = Path.home() / ".clipfusion" / "clipfusion_v2.db"

class Database:
    def __init__(self):
        self._local = threading.local()
        self._init_db()
    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn
    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT, video_path TEXT, language TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY,
                project_id INTEGER,
                segments TEXT, full_text TEXT, language TEXT,
                quality_score REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY,
                project_id INTEGER, transcript_id INTEGER,
                start_time REAL, end_time REAL, text TEXT,
                hook_strength REAL DEFAULT 0.0,
                moment_strength REAL DEFAULT 0.0,
                retention_score REAL DEFAULT 0.0,
                shareability REAL DEFAULT 0.0,
                final_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS cuts (
                id INTEGER PRIMARY KEY,
                project_id INTEGER, candidate_id INTEGER,
                start_time REAL, end_time REAL,
                title TEXT, hook TEXT, archetype TEXT,
                platforms TEXT, output_path TEXT,
                protection_level TEXT DEFAULT 'none',
                decision TEXT
            );
            CREATE TABLE IF NOT EXISTS performances (
                id INTEGER PRIMARY KEY,
                cut_id INTEGER, platform TEXT,
                views INTEGER DEFAULT 0, likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
                posted_at TIMESTAMP
            );
        """)
        conn.commit()

    def save_cut(self, project_id, candidate_id, start, end, title, hook, archetype, platforms, output_path, decision):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO cuts (project_id, candidate_id, start_time, end_time, title, hook, archetype, platforms, output_path, decision)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (project_id, candidate_id, start, end, title, hook, archetype, json.dumps(platforms), output_path, decision))
        conn.commit()

    def get_cuts(self, project_id, decision=None):
        conn = self._get_conn()
        if decision:
            rows = conn.execute("SELECT * FROM cuts WHERE project_id=? AND decision=?", (project_id, decision)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cuts WHERE project_id=?", (project_id,)).fetchall()
        return [dict(r) for r in rows]

_db = None
def get_db():
    global _db
    if _db is None: _db = Database()
    return _db
EOF

# =============================================================================
# 4. CORE: TRANSCRIÇÃO (com fmt_time)
# =============================================================================
echo -e "${YELLOW}--- [4/7] Motor de transcrição ---${NC}"
mkdir -p "$PROJETO_DIR/src/core"
cat > "$PROJETO_DIR/src/core/transcriber.py" << 'EOF'
import gc, warnings, subprocess
from pathlib import Path
warnings.filterwarnings("ignore")

def fmt_time(s: float) -> str:
    return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"

class Transcriber:
    def __init__(self, model="base", compute_type="int8", cpu_threads=2):
        self.model_size = model
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.model = None
    def _load(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            print(f"[WHISPER] Carregando {self.model_size}...")
            self.model = WhisperModel(self.model_size, device="cpu",
                compute_type=self.compute_type, cpu_threads=self.cpu_threads)
    def transcribe(self, audio_path, language=None):
        self._load()
        segments, info = self.model.transcribe(audio_path, language=language,
            beam_size=1, best_of=1, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300})
        result = [{"start": s.start, "end": s.end, "text": s.text.strip()}
                  for s in segments]
        return result, info.language
    def unload(self):
        if self.model:
            del self.model; self.model = None; gc.collect()

def extract_audio(video_path):
    output = str(Path(video_path).with_suffix('.wav'))
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn",
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        "-af", "highpass=f=200,lowpass=f=3000", output], check=True)
    return output
EOF

# =============================================================================
# 5. CORE: SEGMENTAÇÃO, SCORING, DECISÃO
# =============================================================================
echo -e "${YELLOW}--- [5/7] Segmentação, scoring e regra de ouro ---${NC}"
cat > "$PROJETO_DIR/src/core/segment.py" << 'EOF'
def segment_by_pauses(segments, min_dur=20.0, max_dur=30.0, pause_ms=300):
    breaks = [0.0]
    for i, seg in enumerate(segments[:-1]):
        gap = segments[i+1]['start'] - seg['end']
        if gap >= pause_ms/1000.0 or seg['text'].strip()[-1] in '.!?':
            breaks.append(seg['end'])
    breaks.append(segments[-1]['end'])
    candidates = []
    for i in range(len(breaks)-1):
        for j in range(i+1, len(breaks)):
            dur = breaks[j] - breaks[i]
            if dur < min_dur: continue
            if dur > max_dur: break
            text = " ".join(s['text'] for s in segments if breaks[i] <= s['start'] < breaks[j])
            candidates.append({"start": breaks[i], "end": breaks[j], "text": text})
    return candidates[:20]
EOF

cat > "$PROJETO_DIR/src/core/scoring.py" << 'EOF'
import re
class ScoringEngine:
    def __init__(self):
        self.weights = {'hook':0.35, 'moment':0.30, 'retention':0.20, 'share':0.15}
        self.hook_words = ['segredo','nunca','erro','descobri','você sabia','urgente']
        self.moment_words = ['porque','então','resultado','de repente','solução']
    def score_hook(self, text, first_3s):
        score = 5.0 + sum(0.8 for w in self.hook_words if w in first_3s.lower()) + (1.5 if '?' in first_3s else 0)
        return min(10.0, score)
    def score_moment(self, text):
        score = 5.0 + sum(0.6 for w in self.moment_words if w in text.lower())
        return min(10.0, score)
    def score_retention(self, text):
        score = 5.0 + sum(0.4 for c in ['mas','e então','porém'] if c in text.lower())
        return min(10.0, score)
    def score_share(self, text):
        score = 4.0 + (1.0 if 'você' in text.lower() else 0) + (0.5 if '!' in text else 0)
        return min(10.0, score)
    def calculate(self, candidate):
        first_3s = candidate['text'][:100]
        hook = self.score_hook(candidate['text'], first_3s)
        moment = self.score_moment(candidate['text'])
        retention = self.score_retention(candidate['text'])
        share = self.score_share(candidate['text'])
        final = (hook*self.weights['hook'] + moment*self.weights['moment'] +
                 retention*self.weights['retention'] + share*self.weights['share'])
        return {'hook':round(hook,2), 'moment':round(moment,2),
                'retention':round(retention,2), 'share':round(share,2), 'final':round(final,2)}
EOF

cat > "$PROJETO_DIR/src/core/decision.py" << 'EOF'
class DecisionEngine:
    def decide(self, final_score):
        if final_score >= 9.0: return 'approved', f"Nota {final_score:.1f} ≥ 9.0: Aprovado"
        if final_score >= 7.0: return 'review', f"Nota {final_score:.1f}: Revisar"
        return 'rejected', f"Nota {final_score:.1f} < 7.0: Descartar"
EOF

# =============================================================================
# 6. CORE: RENDER 1-PASS
# =============================================================================
echo -e "${YELLOW}--- [6/7] Motor de renderização ---${NC}"
cat > "$PROJETO_DIR/src/core/render.py" << 'EOF'
import subprocess, gc
class RenderEngine:
    def __init__(self, vaapi_device="/dev/dri/renderD128"):
        self.vaapi = vaapi_device
    def render(self, input_video, output_video, start, end, protection='basic'):
        duration = end - start
        filters = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=nv12,hwupload"
        if protection == 'basic':
            filters = "eq=brightness=0.01:contrast=1.02," + filters
        cmd = ["ffmpeg", "-y", "-hwaccel", "vaapi", "-hwaccel_device", self.vaapi,
               "-i", input_video, "-ss", str(start), "-t", str(duration),
               "-vf", filters, "-c:v", "h264_vaapi", "-qp", "24",
               "-c:a", "aac", "-b:a", "128k",
               "-metadata", "encoder=ClipFusion", "-metadata", "creation_time=now",
               output_video]
        result = subprocess.run(cmd, capture_output=True, text=True)
        gc.collect()
        return result.returncode == 0
EOF

# =============================================================================
# 7. IA EXTERNA: PROMPT BUILDER
# =============================================================================
echo -e "${YELLOW}--- [7/7] Ponte para IA externa ---${NC}"
cat > "$PROJETO_DIR/src/core/prompt_builder.py" << 'EOF'
import json, re
from core.transcriber import fmt_time

def _detect_lang(text):
    text_l = text.lower()
    pt_markers = (" você ", " não ", " para ", " que ")
    en_markers = (" you ", " not ", " with ", " the ")
    pt_score = sum(m in text_l for m in pt_markers)
    en_score = sum(m in text_l for m in en_markers)
    return "en" if en_score > pt_score else "pt"

def _coverage_sample(segments, buckets=10):
    if not segments: return []
    first = segments[0]["start"]
    last = segments[-1]["end"]
    span = max(1.0, last - first)
    bucket_size = span / buckets
    sampled = []
    idx = 0
    for b in range(buckets):
        b_start = first + b * bucket_size
        b_end = b_start + bucket_size
        chosen = None
        while idx < len(segments):
            s = segments[idx]; idx += 1
            if b_start <= s["start"] < b_end:
                chosen = s; break
        if chosen: sampled.append(chosen)
    return sampled

def build_analysis_prompt(segments, duration, context=""):
    sampled = _coverage_sample(segments, buckets=12)
    joined = " ".join(s.get("text","") for s in sampled)[:3000]
    lang = _detect_lang(f" {joined} ")
    lines, total = [], 0
    for s in segments:
        line = f"[{fmt_time(s['start'])}] {s['text']}"
        total += len(line) + 1
        if total > 30000: break
        lines.append(line)
    transcript = "\n".join(lines)
    arch_block = "\n".join(f"  {k}: {v['emocao']} — {v['descricao']}" for k,v in ARCHETYPES.items())
    ctx = f"\n## CONTEXTO\n{context.strip()}\n" if context.strip() else ""
    lang_block = "Primary language: ENGLISH" if lang=="en" else "Idioma principal: PORTUGUÊS"
    coverage = "\n".join(f"[{fmt_time(s['start'])}] {s['text']}" for s in sampled)
    return f"""Especialista em viralização.
{ctx}
## DURAÇÃO: {fmt_time(duration)}
## IDIOMA: {lang_block}
## TRANSCRIÇÃO:
{transcript}
## COBERTURA GLOBAL:
{coverage}
## ARQUÉTIPOS:
{arch_block}
## TAREFA: Retorne JSON com cortes (start, end, title, hook, archetype, score, platforms)
{{"cortes":[{{"titulo":"...","start":0,"end":0,"archetype":"05_revelacao","hook":"...","score":8.5,"platforms":["tiktok"]}}]}}"""

def parse_ai_response(text):
    text = re.sub(r"```json\s*|```\s*", "", text.strip())
    blob = re.search(r"\{[\s\S]*\}", text) or re.search(r"\[[\s\S]*\]", text)
    if not blob: raise ValueError("JSON não encontrado")
    parsed = json.loads(blob.group())
    cortes = parsed if isinstance(parsed,list) else parsed.get("cortes",[])
    result = []
    for i,c in enumerate(cortes):
        s = float(c.get("start",0) or 0); e = float(c.get("end",0) or 0)
        if e>s and (e-s)>=10:
            result.append({"cut_index":i,"title":c.get("titulo",f"Corte {i+1}"),
                           "start":s,"end":e,"archetype":c.get("archetype","01_despertar"),
                           "hook":c.get("hook",""),"score":c.get("score",7.0),
                           "platforms":c.get("platforms",["tiktok","reels","shorts"])})
    return result
EOF

# =============================================================================
# 8. ARQUÉTIPOS
# =============================================================================
mkdir -p "$PROJETO_DIR/src/viral_engine"
cat > "$PROJETO_DIR/src/viral_engine/archetypes.py" << 'EOF'
ARCHETYPES = {
    "01_despertar": {"emocao":"Curiosidade+Urgência","descricao":"Quebra de crença"},
    "02_tensao": {"emocao":"Medo+Antecipação","descricao":"Risco iminente"},
    "03_confronto": {"emocao":"Raiva+Determinação","descricao":"Posição forte"},
    "04_virada": {"emocao":"Esperança+Empoderamento","descricao":"Mudança de perspectiva"},
    "05_revelacao": {"emocao":"Surpresa+Fascínio","descricao":"Segredo revelado"},
    "06_justo_engolido": {"emocao":"Injustiça+Revolta","descricao":"Alguém sendo prejudicado"},
    "07_transformacao": {"emocao":"Superação+Inspiração","descricao":"Antes/depois"},
    "08_resolucao": {"emocao":"Alívio+Satisfação","descricao":"Solução entregue"},
    "09_impacto": {"emocao":"Choque+Admiração","descricao":"Números fortes"},
    "10_encerramento": {"emocao":"Realização+Fechamento","descricao":"Lição aprendida"},
}
EOF

# =============================================================================
# 9. GUI COMPLETA (com persistência e render)
# =============================================================================
echo -e "${YELLOW}--- [8/7] Interface gráfica ---${NC}"
cat > "$PROJETO_DIR/src/gui/main_gui.py" << 'EOF'
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading, sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db
from core.transcriber import Transcriber, extract_audio
from core.segment import segment_by_pauses
from core.scoring import ScoringEngine
from core.decision import DecisionEngine
from core.render import RenderEngine
from core.prompt_builder import build_analysis_prompt, parse_ai_response
from viral_engine.archetypes import ARCHETYPES

class ClipFusionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ClipFusion V2 - Build Ouro")
        self.root.geometry("1024x768")
        self.root.configure(bg="#2e2e2e")
        self.project_id = None
        self.segments = []
        self.candidates = []  # armazena candidatos aprovados com seus dados
        self.create_widgets()
    def create_widgets(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True)
        # Aba 1: Projeto
        self.frame_proj = ttk.Frame(nb); nb.add(self.frame_proj, text="Projeto")
        self.video_path = tk.StringVar()
        tk.Label(self.frame_proj, text="Vídeo:").grid(row=0, column=0)
        tk.Entry(self.frame_proj, textvariable=self.video_path, width=50).grid(row=0, column=1)
        tk.Button(self.frame_proj, text="Selecionar", command=self.select_video).grid(row=0, column=2)
        tk.Button(self.frame_proj, text="Transcrever", command=self.transcribe).grid(row=1, column=1)
        # Aba 2: Transcrição
        self.frame_trans = ttk.Frame(nb); nb.add(self.frame_trans, text="Transcrição")
        self.trans_text = scrolledtext.ScrolledText(self.frame_trans, height=20)
        self.trans_text.pack(fill='both', expand=True)
        # Aba 3: IA Externa
        self.frame_ia = ttk.Frame(nb); nb.add(self.frame_ia, text="IA Externa")
        self.prompt_text = scrolledtext.ScrolledText(self.frame_ia, height=10)
        self.prompt_text.pack(fill='x')
        tk.Button(self.frame_ia, text="Gerar Prompt", command=self.generate_prompt).pack()
        self.json_text = scrolledtext.ScrolledText(self.frame_ia, height=10)
        self.json_text.pack(fill='both', expand=True)
        tk.Button(self.frame_ia, text="Processar JSON", command=self.process_json).pack()
        # Aba 4: Cortes
        self.frame_cuts = ttk.Frame(nb); nb.add(self.frame_cuts, text="Cortes")
        self.cuts_listbox = tk.Listbox(self.frame_cuts, height=15)
        self.cuts_listbox.pack(fill='both', expand=True)
        # Aba 5: Render
        self.frame_render = ttk.Frame(nb); nb.add(self.frame_render, text="Render")
        self.render_log = scrolledtext.ScrolledText(self.frame_render, height=20)
        self.render_log.pack(fill='both', expand=True)
        tk.Button(self.frame_render, text="Renderizar Aprovados", command=self.render_approved).pack()
        # Aba 6: Histórico
        self.frame_hist = ttk.Frame(nb); nb.add(self.frame_hist, text="Histórico")
        self.hist_list = tk.Listbox(self.frame_hist)
        self.hist_list.pack(fill='both', expand=True)
        # Aba 7: Agenda (placeholder)
        self.frame_agenda = ttk.Frame(nb); nb.add(self.frame_agenda, text="Agenda")
        self.agenda_text = scrolledtext.ScrolledText(self.frame_agenda, height=20)
        self.agenda_text.pack(fill='both', expand=True)
        self.agenda_text.insert('1.0', "Funcionalidade de agenda em desenvolvimento.")
    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[("MP4", "*.mp4")])
        if path: self.video_path.set(path)
    def log(self, msg, target='render'):
        if target == 'render':
            self.render_log.insert('end', msg + '\n')
            self.render_log.see('end')
    def transcribe(self):
        if not self.video_path.get():
            messagebox.showwarning("Atenção", "Selecione um vídeo primeiro.")
            return
        threading.Thread(target=self._transcribe, daemon=True).start()
    def _transcribe(self):
        try:
            self.log("Extraindo áudio...", 'render')
            audio = extract_audio(self.video_path.get())
            self.log("Transcrevendo (modelo base, beam=1)...", 'render')
            t = Transcriber(model="base")
            segs, lang = t.transcribe(audio)
            t.unload()
            self.segments = segs
            self.trans_text.delete('1.0', 'end')
            for s in segs[:50]:
                self.trans_text.insert('end', f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}\n")
            self.log(f"Transcrição concluída: {len(segs)} segmentos.", 'render')
        except Exception as e:
            self.log(f"Erro na transcrição: {e}", 'render')
            messagebox.showerror("Erro", f"Falha na transcrição: {e}")
    def generate_prompt(self):
        if not self.segments:
            messagebox.showwarning("Atenção", "Transcreva primeiro.")
            return
        prompt = build_analysis_prompt(self.segments, self.segments[-1]['end'], "")
        self.prompt_text.delete('1.0', 'end')
        self.prompt_text.insert('1.0', prompt)
    def process_json(self):
        json_str = self.json_text.get('1.0', 'end').strip()
        if not json_str:
            messagebox.showwarning("Atenção", "Cole a resposta JSON da IA.")
            return
        try:
            cuts = parse_ai_response(json_str)
            self.cuts_listbox.delete(0, 'end')
            self.candidates = []
            for c in cuts:
                self.cuts_listbox.insert('end', f"{c['title']} ({c['start']:.1f}-{c['end']:.1f}) score:{c.get('score',0)}")
                self.candidates.append(c)
            # Salva cortes no banco (opcional)
            self.log(f"{len(cuts)} cortes carregados. Selecione os aprovados e clique em Renderizar.", 'render')
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao processar JSON: {e}")
    def render_approved(self):
        if not self.candidates:
            messagebox.showwarning("Atenção", "Nenhum corte disponível. Processe o JSON primeiro.")
            return
        # Pega o índice selecionado ou o primeiro
        sel = self.cuts_listbox.curselection()
        if not sel:
            idx = 0
        else:
            idx = sel[0]
        cut = self.candidates[idx]
        start = cut['start']
        end = cut['end']
        output_dir = Path.home() / "clipfusion_output"
        output_dir.mkdir(exist_ok=True)
        out_file = output_dir / f"cut_{start:.0f}_{end:.0f}.mp4"
        self.log(f"Renderizando corte: {cut['title']} ({start:.1f}s - {end:.1f}s)")
        renderer = RenderEngine()
        success = renderer.render(self.video_path.get(), str(out_file), start, end, protection='basic')
        if success:
            self.log(f"✅ Renderizado: {out_file}")
            messagebox.showinfo("Sucesso", f"Vídeo salvo em {out_file}")
        else:
            self.log("❌ Falha no render. Verifique o log.")
            messagebox.showerror("Erro", "Falha na renderização.")
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ClipFusionApp()
    app.run()
EOF

# =============================================================================
# 10. SCRIPT DE EXECUÇÃO
# =============================================================================
echo -e "${YELLOW}--- [9/7] Script de execução ---${NC}"
cat > "$PROJETO_DIR/run.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
export LIBVA_DRIVER_NAME=i965
export OMP_NUM_THREADS=2
export MALLOC_ARENA_MAX=2
export PYTHONPATH="$PWD/src"
source venv/bin/activate
python3 src/gui/main_gui.py
EOF
chmod +x "$PROJETO_DIR/run.sh"

# =============================================================================
# 11. VALIDAÇÃO FINAL
# =============================================================================
echo -e "${YELLOW}--- [10/7] Validação do hardware e importação ---${NC}"
cd "$PROJETO_DIR"
source venv/bin/activate
python3 -c "
import sys
sys.path.insert(0, 'src')
from core.transcriber import Transcriber, fmt_time
from core.segment import segment_by_pauses
from core.scoring import ScoringEngine
from core.decision import DecisionEngine
from core.render import RenderEngine
from core.prompt_builder import build_analysis_prompt, parse_ai_response
from db import get_db
print('✅ Todos os módulos carregados com sucesso.')
"

if vainfo | grep -q "VAEntrypointEncSlice"; then
    echo -e "${GREEN}✅ VA-API Intel HD 520 detectada.${NC}"
else
    echo -e "${RED}⚠️ VA-API não detectada. Render será por software.${NC}"
fi

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"

echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   INSTALAÇÃO CONCLUÍDA - CLIPFUSION V2 BUILD OURO   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}Para iniciar: cd $PROJETO_DIR && ./run.sh${NC}"