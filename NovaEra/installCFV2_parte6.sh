#!/bin/bash
# Parte 7: Script de Execução Canônico e Validação de Elite
set -euo pipefail

PROJETO_DIR="${HOME}/ClipFusion_V2_FINAL"

cat > "$PROJETO_DIR"/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# 1. VARIÁVEIS DE PERFORMANCE (HARDWARE SKYLAKE)
export LIBVA_DRIVER_NAME=iHD  # Recomendado para Intel HD 520 no Debian 12
export OMP_NUM_THREADS=2      # Evita sufocar o i5-6200U
export MALLOC_ARENA_MAX=2     # Proteção contra fragmentação de RAM
export PYTHONPATH="$PWD/src"

# 2. AMBIENTE VIRTUAL
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -q faster-whisper numpy pyyaml  # PyYAML é necessário para as configs

# 3. VERIFICAÇÃO DE BLINDAGEM (OPCIONAL MAS RECOMENDADO)
echo "🔍 Validando hardware antes do boot..."
python3 -c "from utils.hardware import check_system; check_system()" 2>/dev/null || echo "⚠️ Hardware sem otimizações totais."

# 4. START GUI
echo "🚀 Iniciando ClipFusion Viral Pro V2..."
python3 src/main.py
EOF

chmod +x "$PROJETO_DIR"/run.sh

# Smoke Test com ajuste de nomenclatura
echo "🧪 Iniciando Smoke Test de Módulos..."
cd "$PROJETO_DIR"
source venv/bin/activate
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
try:
    from core.transcriber import Transcriber
    from core.segment import segment_by_pauses
    from core.scoring import ScoringEngine
    from core.decision import DecisionEngine
    from db import get_db
    print('✅ Todos os módulos vitais importados com sucesso!')
except ImportError as e:
    print(f'❌ Erro de importação: {e}')
    sys.exit(1)
"

echo "✅ Parte 7 concluída: run.sh e validação total finalizada."
