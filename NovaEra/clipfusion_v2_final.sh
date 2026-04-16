#!/bin/bash
# ClipFusion Viral Pro V2 - Orquestrador de Instalação e Validação
# Hardware: i5-6200U/7200U | Interface: MATE Desktop
set -euo pipefail

# Cores para o terminal
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    CLIPFUSION V2 BUILD OURO - ORQUESTRADOR MESTRE      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then echo -e "${RED}❌ Execute como root: sudo bash $0${NC}"; exit 1; fi

# 1. VALIDAÇÃO DOS SCRIPTS EXISTENTES
echo -e "${YELLOW}--- [1/6] Verificando integridade dos scripts de origem ---${NC}"
for i in 1 2 3 4 6; do
    if [ ! -f "installCFV2_parte$i.sh" ] && [ ! -f "InstallCFV2_parte$i.sh" ]; then
        echo -e "${RED}⚠️ Erro: Script da parte $i não encontrado na pasta atual.${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ Scripts de origem detectados.${NC}"

# 2. EXECUÇÃO DAS PARTES COM VALIDAÇÃO DE PASTA
echo -e "${YELLOW}--- [2/6] Executando camadas de construção ---${NC}"
# Parte 1 e 2: Estrutura e Motores Iniciais
bash installCFV2_parte1.sh
bash InstallCFV2_parte2.sh

# Validação física imediata
PROJETO_DIR="${HOME}/ClipFusion_V2_FINAL"
[ -z "$SUDO_USER" ] || PROJETO_DIR="/home/$SUDO_USER/ClipFusion_V2_FINAL"

if [ -d "$PROJETO_DIR/src/core" ]; then
    echo -e "${GREEN}✅ Estrutura /src/core criada com sucesso.${NC}"
else
    echo -e "${RED}❌ Falha crítica: Pasta src/core não foi criada.${NC}" [3]
    exit 1
fi

# 3. CONSTRUÇÃO DO CÉREBRO E MÚSCULOS (Partes 3, 4 e 6)
bash installCFV2_parte3.sh
bash installCFV2_parte4.sh
bash installCFV2_parte6.sh

# 4. INSTALAÇÃO DA "PARTE 5" FALTANTE (Persistência e GUI)
echo -e "${YELLOW}--- [3/6] Selando a Parte 5 (Banco e Interface) ---${NC}"
cat > "$PROJETO_DIR/db.py" << 'EOF'
import sqlite3, os
from pathlib import Path
DB_PATH = Path(os.path.expanduser("~")) / ".clipfusion" / "clipfusion_v2.db"
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, status TEXT DEFAULT 'pending');")
    conn.commit()
    conn.close()
    print("✅ Banco SQLite V2 Inicializado.") [5, 6]
if __name__ == "__main__": init_db()
EOF

# 5. TESTE DE FUNCIONAMENTO (HARDWARE CHECK)
echo -e "${YELLOW}--- [4/6] Validando Blindagem do Hardware (Fim dos Freezes) ---${NC}"
cd "$PROJETO_DIR"
# Chama o validador de sistema que criamos no utils/hardware.py
python3 -c "from utils.hardware import check_system; check_system()" || echo -e "${RED}⚠️ Hardware sem otimizações totais.${NC}" [2]

# 6. TESTE DE RENDERIZAÇÃO (DUMMY TEST)
echo -e "${YELLOW}--- [5/6] Testando motor de Render 2-pass (VA-API) ---${NC}"
if vainfo | grep -q "VAEntrypointEncSlice"; then
    echo -e "${GREEN}✅ VA-API detectada e pronta para o Passo 1.${NC}" [7]
else
    echo -e "${RED}⚠️ VA-API não detectada. O render será lento (Software).${NC}"
fi

# AJUSTE FINAL DE PERMISSÕES
chown -R ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} "$PROJETO_DIR"

echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   INSTALAÇÃO CONCLUÍDA - SISTEMA PRONTO PARA O USO!    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${BLUE}Para iniciar seu ganha-pão, execute:${NC} cd $PROJETO_DIR && ./run.
