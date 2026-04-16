# ClipFusionV1 – Mapa do Sistema

*Gerado em: 2026-04-14*

Este documento descreve a estrutura canônica do projeto **ClipFusionV1**
conforme os requisitos de estabilização.  Todos os diretórios
e arquivos principais são listados com uma breve descrição de sua
responsabilidade.

## Estrutura de Diretórios

- **ClipFusionV1/** – Raiz do pacote Python.  Contém todo o
  código fonte da aplicação.
  - **app/** – Entrada CLI/GUI da aplicação.
  - **core/** – Módulos centrais: banco de dados, pipeline,
    segmentação, ASR, scoring e fila de jobs.
  - **viral_engine/** – Analisador de nichos, gerador de hooks e
    recomendador de agenda.
  - **anti_copy_modules/** – Implementações de proteção: básica,
    Anti‑IA e máxima.
  - **gui/** – Interface gráfica (Tkinter) em várias abas.
  - **infra/** – Componentes de infraestrutura e utilidades comuns.
  - **config/** – Futuras configurações (atualmente vazio).
  - **installers/** – Scripts de instalação específicos do
    sistema (ex.: `install_debian.sh`).
  - **run/** – Scripts de execução (`run.sh`, `preflight.sh`,
    `run_queue.sh`).
  - **tests/** – Espaço reservado para scripts de teste automatizado.
  - **output/** – Diretório de saída para vídeos processados e
    relatórios.  Contém subdiretórios `videos/` e `reports/`.
  - **docs/** – Documentação interna (este arquivo, changelog,
    guia de instalação etc.).
  - **requirements/** – Arquivos de dependências Python (a definir).
  - **tools/** – Ferramentas auxiliares.

## Principais Módulos

 - **core/database.py** – Implementa um banco de dados SQLite sem
   dependências externas (usa apenas a biblioteca padrão `sqlite3`).
   Fornece funções para inicializar a base, inserir projetos, jobs,
   clipes e consultar registros.
- **core/asr.py** – Transcrição de áudio com fallback para texto
  fictício caso a biblioteca Whisper não esteja instalada.
- **core/segmentation.py** – Divide o vídeo em segmentos de
  duração máxima configurável usando heurística temporal.
- **core/scoring.py** – Atribui scores de viralidade de forma
  decrescente ao longo dos segmentos.
- **core/pipeline.py** – Orquestra transcrição, segmentação,
  scoring, aplicação de proteção e persistência.
- **core/queue.py** – Loop de processamento de jobs em fila.
- **viral_engine/engine.py** – Detecta nicho, gera ganchos e
  produz horários anti‑padrão para postagem.
- **anti_copy_modules/basic.py** – Proteção básica (zoom, eq,
  metadados, normalização de áudio).
- **anti_copy_modules/anti_ia.py** – Proteção Anti‑IA (ruído e
  chroma).
- **anti_copy_modules/maximum.py** – Proteção máxima (zoom mais
  agressivo, ruído intenso e variação de pitch).
- **gui/main.py** – Implementação da interface gráfica com abas.
- **run/preflight.sh** – Checa ffmpeg, Python, espaço em disco,
  permissões de escrita e biblioteca Whisper.
- **run/run.sh** – Wrapper de execução para a CLI Python.
- **run/run_queue.sh** – Script para processar a fila.
- **installers/install_debian.sh** – Instala dependências de
  sistema e Python em Debian/Ubuntu.
- **FULLinstallClipFusionV1.sh** – Script unificado que
  instala dependências, executa preflight e realiza um smoke test.

## Fluxo de Processamento

1. **Ingestão** – O usuário seleciona um vídeo via CLI ou GUI.
2. **Transcrição** – O áudio é extraído e, se possível,
   transcrito via Whisper; caso contrário, um texto fictício é
   usado para manter o fluxo.
3. **Segmentação** – O vídeo é dividido em partes de até 60s.
4. **Scoring** – Cada segmento recebe uma pontuação de
   viralidade (80, 70, 60, ...).
5. **IA Externa** – O ViralAnalyzer detecta o nicho, gera ganchos
   e atribui arquétipos emocionais aos segmentos.
6. **Decisão** – Os melhores três segmentos são selecionados
   automaticamente.
7. **Render** – Cada segmento é cortado com ffmpeg e
   protegido de acordo com o nível escolhido.
8. **Persistência** – Os dados são gravados no SQLite e os
   arquivos resultantes ficam em `output/videos`.
9. **Histórico e Agenda** – O usuário pode consultar clips
   anteriores e receber sugestões de horários de publicação.
