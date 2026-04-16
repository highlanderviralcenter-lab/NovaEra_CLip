#!/bin/bash
# Script 5: Database e GUI de 7 Abas
set -euo pipefail

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"

echo "--- 1. CRIANDO BANCO UNIFICADO (Fim das notas zeradas) ---"
cat > "$PROJETO_DIR/db.py" << 'EOF'
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".clipfusion" / "clipfusion_v2.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    # Schema unificado com DEFAULT 0.0 garante que o sistema nunca fique "cego" [3, 5]
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, video_path TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY, project_id INTEGER, start REAL, end REAL, text TEXT,
            hook_score REAL DEFAULT 0.0, retention_score REAL DEFAULT 0.0, combined_score REAL DEFAULT 0.0
        );
    """)
    conn.commit()
    conn.close()

def normalize_scores(scores):
    # Correção do "fio trocado": mapeia campos legados para o novo padrão [3, 6]
    if "retencao_estimada" in scores:
        scores["retention_score"] = scores.pop("retencao_estimada")
    return scores
EOF

echo "--- 2. CRIANDO INTERFACE HUMANA (src/gui/main_gui.py) ---"
cat > "$PROJETO_DIR/src/gui/main_gui.py" << 'EOF'
import tkinter as tk
from tkinter import ttk

class ClipFusionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("✂ ClipFusion Viral Pro V2")
        self.root.geometry("1100x750")
        self._build_tabs()

    def _build_tabs(self):
        # As 7 abas exigidas pelo seu Manual Master [4, 7]
        tab_control = ttk.Notebook(self.root)
        tabs = ["Projeto", "Transcrição", "IA Externa", "Cortes", "Render", "Histórico", "Agenda"]
        for name in tabs:
            tab = ttk.Frame(tab_control)
            tab_control.add(tab, text=name)
        tab_control.pack(expand=1, fill="both")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    ClipFusionApp().run()
EOF

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"
echo "✅ Script 5 finalizado. O Frankenstein agora tem memória e rosto."
