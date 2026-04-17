import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading, os
from pathlib import Path
from datetime import datetime
import db as db
from core.cut_engine import render_all
from core.transcriber import fmt_time

BG = "#0d0d1a"
BG2 = "#151528"
BG3 = "#1e1e3a"
ACC = "#7c3aed"
GRN = "#22c55e"
WHT = "#ffffff"

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ClipFusion - Corte com Legenda")
        self.root.geometry("800x700")
        self.root.configure(bg=BG)
        self.video_path = None
        self.project_id = None
        self.segments = []
        self._build()

    def _build(self):
        f = tk.Frame(self.root, bg=BG2)
        f.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(f, text="ClipFusion Viral Pro", font=("Arial", 16), bg=BG2, fg=WHT).pack(pady=(0,10))

        # Botão selecionar vídeo
        row1 = tk.Frame(f, bg=BG2)
        row1.pack(fill="x", pady=5)
        tk.Button(row1, text="📂 Selecionar Vídeo", command=self.sel_video, bg=ACC, fg=WHT).pack(side="left")
        self.lbl_video = tk.Label(row1, text="Nenhum vídeo", bg=BG2, fg=GRN)
        self.lbl_video.pack(side="left", padx=10)

        # Área de texto para legenda (transcrição manual)
        tk.Label(f, text="Digite ou cole a transcrição (uma frase por linha):", bg=BG2, fg=WHT).pack(anchor="w", pady=(10,0))
        self.txt = scrolledtext.ScrolledText(f, height=12, bg=BG3, fg=WHT, font=("Consolas",10))
        self.txt.pack(fill="both", expand=True, pady=5)

        # Botão processar
        tk.Button(f, text="✂️ Segmentar e Renderizar", command=self.processar, bg=GRN, fg=WHT, font=("Arial",10,"bold")).pack(pady=10)

        # Log
        tk.Label(f, text="Log:", bg=BG2, fg=WHT).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(f, height=8, bg=BG3, fg=GRN, font=("Consolas",9))
        self.log.pack(fill="x", pady=5)

    def sel_video(self):
        p = filedialog.askopenfilename(filetypes=[("MP4","*.mp4")])
        if p:
            self.video_path = p
            self.lbl_video.config(text=os.path.basename(p))
            self.log_insert(f"Vídeo selecionado: {p}\n")

    def processar(self):
        if not self.video_path:
            self.log_insert("❌ Selecione um vídeo primeiro.\n")
            return
        texto = self.txt.get("1.0", "end").strip()
        if not texto:
            self.log_insert("❌ Digite ou cole a transcrição.\n")
            return
        lines = [l.strip() for l in texto.splitlines() if l.strip()]
        self.log_insert(f"📝 {len(lines)} linhas de texto.\n")

        # Cria segmentos base (cada linha = 3 segundos)
        base = [{"start": i*3.0, "end": (i+1)*3.0, "text": line} for i, line in enumerate(lines)]
        self.segments = self._merge_segments(base)
        if not self.segments:
            self.log_insert("❌ Erro na segmentação.\n")
            return
        self.log_insert(f"📦 {len(self.segments)} segmentos criados (18-35s cada).\n")

        # Salva projeto e cortes no banco
        nome = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.project_id = db.create_project(nome, self.video_path)
        db.save_transcription(self.project_id, "\n".join(lines), self.segments)
        cuts = [{"start": s["start"], "end": s["end"], "title": f"Corte {i+1}", "platforms": ["tiktok"]} for i, s in enumerate(self.segments)]
        db.save_cuts(self.project_id, cuts)
        self.log_insert(f"💾 Projeto ID {self.project_id} salvo.\n")

        # Pasta de saída
        out_dir = Path(self.video_path).parent / "clipfusion_output"
        out_dir.mkdir(exist_ok=True)

        self.log_insert("🎬 Iniciando renderização...\n")
        threading.Thread(target=self._render_thread, args=(cuts, out_dir), daemon=True).start()

    def _render_thread(self, cuts, out_dir):
        try:
            render_all(
                self.video_path, cuts, self.segments, str(out_dir), str(self.project_id),
                ace_level="basic",
                use_vaapi=True,   # altere para False se não quiser usar VA-API
                progress_cb=lambda m: self.root.after(0, lambda: self.log_insert(m + "\n"))
            )
            self.root.after(0, lambda: self.log_insert(f"✅ Render concluído! Cortes salvos em {out_dir}\n"))
            self.root.after(0, lambda: messagebox.showinfo("Pronto", f"Vídeos gerados em {out_dir}"))
        except Exception as e:
            self.root.after(0, lambda: self.log_insert(f"❌ Erro no render: {e}\n"))

    def _merge_segments(self, base, min_dur=18, max_dur=35, gap=0.5):
        merged = []
        if not base:
            return merged
        cur = dict(base[0])
        for seg in base[1:]:
            if seg["start"] - cur["end"] < gap and seg["end"] - cur["start"] <= max_dur:
                cur["end"] = seg["end"]
                cur["text"] += " " + seg["text"]
            else:
                if cur["end"] - cur["start"] < min_dur:
                    cur["end"] = cur["start"] + min_dur
                merged.append(cur)
                cur = dict(seg)
        if cur["end"] - cur["start"] < min_dur:
            cur["end"] = cur["start"] + min_dur
        merged.append(cur)
        return merged

    def log_insert(self, msg):
        self.log.insert("end", msg)
        self.log.see("end")
        self.root.update_idletasks()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
