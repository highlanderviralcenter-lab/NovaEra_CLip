#!/bin/bash
# Instalador completo para o ClipFusionV1.
# Este script prepara o ambiente, executa verificacoes pre-flight e
# realiza um teste simples de ponta a ponta para validar a
# instalacao.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[ClipFusionV1] Inicio da instalacao completa."

# Executa script de instalacao de dependencias
bash "$ROOT_DIR/installers/install_debian.sh"

# Executa pre-flight usando bash explicitamente (evita problemas com sistemas montados como noexec)
bash "$ROOT_DIR/run/preflight.sh"

echo "[ClipFusionV1] Pre-flight ok. Realizando smoke test..."

# Criar video de exemplo (sempre reescreve para garantir integridade)
SAMPLE_VIDEO="$ROOT_DIR/output/sample_input.mp4"
mkdir -p "$ROOT_DIR/output"
echo "[ClipFusionV1] Gerando vídeo de exemplo..."
# Exporta a variável SAMPLE_VIDEO para o ambiente do Python
env SAMPLE_VIDEO="$SAMPLE_VIDEO" python3 - <<'PY'
import os
import cv2
import numpy as np
out_path = os.environ.get('SAMPLE_VIDEO', 'sample_input.mp4')
width, height = 640, 480
fps = 30
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
for i in range(int(fps * 3)):
    # Gera um gradiente de cores em movimento
    img = np.zeros((height, width, 3), dtype=np.uint8)
    color = (i % 255, (2*i) % 255, (3*i) % 255)
    img[:] = color
    writer.write(img)
writer.release()
PY

# Processar video via CLI
python3 -m ClipFusionV1.app.main process --input "$SAMPLE_VIDEO" --name "TesteSmoke" --protection basic

echo "[ClipFusionV1] Smoke test finalizado."

# Gerar relatorio
REPORT="$ROOT_DIR/output/reports/install_report.md"
mkdir -p "$(dirname "$REPORT")"
{
    echo "# Relatorio de instalacao ClipFusionV1"
    echo "Data: $(date)"
    echo ""
    echo "## Comandos executados"
    echo "- install_debian.sh"
    echo "- preflight.sh"
    echo "- Smoke test via process"
    echo ""
    echo "## Status"
    echo "Todas as etapas concluídas sem erros."
} > "$REPORT"

echo "[ClipFusionV1] Instalacao completa com sucesso. Relatorio em $REPORT"
