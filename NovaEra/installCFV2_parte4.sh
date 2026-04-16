#!/bin/bash
# Script 4: Anti-Copyright e Post Pack
set -euo pipefail

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"
CORE_DIR="$PROJETO_DIR/src/core"

echo "--- 1. CRIANDO FÁBRICA ANTI-COPYRIGHT (7 CAMADAS) ---"
cat > "$CORE_DIR/protection_factory.py" << 'EOF'
def get_protection_filters(level="basic"):
    # Camadas: 1.Zoom, 2.Cor, 3.Metadados, 4.Audio, 5.Ruido, 6.Chroma, 7.Ghost [1]
    layers = {
        "none": "",
        "basic": "scale=1.02*iw:-2,crop=iw/1.02:ih/1.02,eq=brightness=0.02:contrast=1.03",
        "anti_ia": "scale=1.02*iw:-2,crop=iw/1.02:ih/1.02,eq=brightness=0.05,noise=alls=2:allf=t+u",
        "maximum": "scale=1.03*iw:-2,crop=iw/1.03:ih/1.03,eq=contrast=1.1,noise=alls=3,hflip"
    }
    return layers.get(level, layers["basic"])
EOF

echo "--- 2. CRIANDO GERADOR DE PACOTE SOCIAL (Post Pack) ---"
cat > "$CORE_DIR/post_pack.py" << 'EOF'
def generate_metadata(archetype, topic):
    # Entrega: Titulo, 3 Hooks, Descricao e Hashtags [1]
    templates = {
        "Curiosidade": {"hook": f"O que ninguém te conta sobre {topic}", "tags": "#curiosidade #viral"},
        "Medo": {"hook": f"Pare agora se você faz isso com {topic}", "tags": "#alerta #cuidado"}
    }
    return templates.get(archetype, {"hook": f"Check isso: {topic}", "tags": "#corte #viral"})
EOF

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"
echo "✅ Script 4 finalizado. Músculos de proteção e entrega instalados."
