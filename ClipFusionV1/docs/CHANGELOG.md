# Changelog – ClipFusionV1

Todas as alterações significativas neste repositório são documentadas
neste arquivo.  As entradas são organizadas cronologicamente.

## 2026‑04‑14

### Added

- Estrutura inicial do projeto **ClipFusionV1** baseada em
  especificações aprovadas, com diretórios `app`, `core`,
  `anti_copy_modules`, `viral_engine`, `gui`, `infra`, `config`,
  `installers`, `run`, `tests`, `output`, `docs`, `requirements` e
  `tools`.
- Banco de dados SQLite com tabelas `projects`, `video_clips`,
  `jobs` e `post_schedules` (`core/database.py`).
- Pipeline de processamento completo (`core/pipeline.py`) incluindo
  transcrição (fallback via texto fixo), segmentação, scoring,
  geração de ganchos e renderização com proteção.
- Módulos de proteção `BasicProtection`, `AntiIAProtection` e
  `MaximumProtection` usando ffmpeg.
- Analisador viral (`viral_engine/engine.py`) com nichos,
  arquétipos e agenda anti‑padrão.
- Interface gráfica simplificada com sete abas (`gui/main.py`).
- CLI com subcomandos `process`, `enqueue`, `list` e
  `run_queue` (`app/main.py`).
- Scripts bash: `run.sh`, `preflight.sh`, `run_queue.sh`,
  `install_debian.sh` e `FULLinstallClipFusionV1.sh` com smoke test.
- Documentos `SYSTEM_MAP.md`, `CHANGELOG.md` e `GUIA_INSTALACAO_DEBIAN.md`.

### Changed

- Todo o código foi renomeado e reorganizado para utilizar o nome
  canônico `ClipFusionV1`, conforme as regras de renomeação.

  - Substituído o uso de `SQLAlchemy` por funções de banco usando
    `sqlite3` da biblioteca padrão.  Isso elimina a necessidade de
    instalar dependências externas via pip.
  - Ajustes nos scripts de instalação para não instalar pacotes via
    `pip`; o instalador agora apenas verifica ferramentas como
    `python3` e `ffmpeg` e deixa a instalação de pacotes de
    sistema a cargo do usuário.

### Notes

- Esta é a primeira versão consolidada da série ClipFusion
  reconstruída para execução em hardware modesto (Intel i5‑6200U
  com 8GB de RAM), com foco em simplicidade e estabilidade.
