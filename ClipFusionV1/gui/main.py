"""
Interface gráfica minimalista do ClipFusionV1.

Esta GUI utiliza Tkinter para criar uma janela com múltiplas abas,
permitindo ao usuário selecionar um vídeo, iniciar o processamento e
visualizar histórico.  Devido a limitações de hardware, a interface
é propositalmente simples, mas cobre as principais etapas do
workflow.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

from ..core.pipeline import Pipeline
from ..core.database import list_clips, get_project


class ClipFusionGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ClipFusionV1")
        self.geometry("800x600")
        self.pipeline = Pipeline()
        self._build_ui()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)
        # Aba Projeto
        tab_project = ttk.Frame(notebook)
        self._build_project_tab(tab_project)
        notebook.add(tab_project, text="Projeto")
        # Abas simplificadas para as demais fases
        for name in ["Transcrição", "IA Externa", "Cortes", "Render", "Histórico", "Agenda"]:
            frame = ttk.Frame(notebook)
            if name == "Histórico":
                self._build_history_tab(frame)
            else:
                ttk.Label(frame, text=f"Função {name} simplificada nesta versão.").pack(pady=20)
            notebook.add(frame, text=name)

    # Project tab building
    def _build_project_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Selecione um vídeo para processar:").pack(pady=10)
        file_var = tk.StringVar()
        name_var = tk.StringVar(value="Projeto")
        protection_var = tk.StringVar(value="basic")
        entry = ttk.Entry(frame, textvariable=file_var, width=60)
        entry.pack(side=tk.LEFT, padx=5)
        def browse_file():
            path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4"), ("Todos", "*.*")])
            if path:
                file_var.set(path)
                name_var.set(os.path.splitext(os.path.basename(path))[0])
        ttk.Button(frame, text="Buscar", command=browse_file).pack(side=tk.LEFT)
        ttk.Label(frame, text="Nome do projeto:").pack(pady=5)
        ttk.Entry(frame, textvariable=name_var, width=40).pack(pady=5)
        ttk.Label(frame, text="Proteção:").pack(pady=5)
        protection_options = ["none", "basic", "anti_ia", "maximum"]
        ttk.OptionMenu(frame, protection_var, protection_var.get(), *protection_options).pack(pady=5)
        def start_processing():
            video = file_var.get()
            if not video:
                messagebox.showwarning("Aviso", "Selecione um vídeo.")
                return
            try:
                self.pipeline.process(video, name_var.get(), protection_var.get())
                messagebox.showinfo("Sucesso", "Processamento concluído!")
            except Exception as e:
                logging.exception("Erro no processamento:")
                messagebox.showerror("Erro", str(e))
        ttk.Button(frame, text="Iniciar", command=start_processing).pack(pady=20)

    # History tab building
    def _build_history_tab(self, frame: ttk.Frame) -> None:
        self.history_tree = ttk.Treeview(frame, columns=("ID", "Projeto", "Clip", "Score", "Arquivo"), show="headings")
        for col in ("ID", "Projeto", "Clip", "Score", "Arquivo"):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="Atualizar", command=self._load_history).pack(pady=5)
        self._load_history()

    def _load_history(self) -> None:
        for i in self.history_tree.get_children():
            self.history_tree.delete(i)
        clips = list_clips()
        for clip in clips:
            project = get_project(clip["project_id"])
            start = clip["start_time"]
            end = clip["end_time"]
            self.history_tree.insert(
                "",
                tk.END,
                values=(
                    clip["id"],
                    project["name"] if project else "?",
                    f"{start}-{end}",
                    clip["viral_score"],
                    os.path.basename(clip["output_path"]),
                ),
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = ClipFusionGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
