#!/bin/bash
set -e
GRN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok() { echo -e "${GRN}[✓]${NC} $1"; }
warn() { echo -e "${YEL}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "╔═════════════════════════════════════════╗"
echo "║  ClipFusion Viral Pro — Instalação     ║"
echo "║  Hardware: i5-6200U + Intel HD 520     ║"
echo "╚═════════════════════════════════════════╝"
echo ""

if ! grep -q "i915.enable_guc=3" /proc/cmdline; then
    warn "Kernel sem i915.enable_guc=3 — execute o Debian Tunado 3.0 primeiro."
fi

sudo apt update -qq
sudo apt install -y python3 python3-pip python3-venv python3-tk \
    ffmpeg git curl wget intel-media-va-driver-non-free \
    libva-drm2 libva-x11-2 libva-glx2 i965-va-driver-shaders \
    vainfo intel-gpu-tools lm-sensors 2>/dev/null || true
ok "Dependências do sistema"

export LIBVA_DRIVER_NAME=iHD
if vainfo 2>&1 | grep -q "VAEntrypointEncSlice"; then
    ok "VA-API Intel HD 520 — H.264 encode disponível"
elif vainfo 2>&1 | grep -q "i965"; then
    warn "VA-API driver i965 (fallback)"
else
    warn "VA-API não detectado — render usará CPU"
fi

if ! grep -q "LIBVA_DRIVER_NAME" ~/.bashrc 2>/dev/null; then
    echo 'export LIBVA_DRIVER_NAME=iHD' >> ~/.bashrc
    echo 'export LIBVA_DRIVERS_PATH=/usr/lib/x86_64-linux-gnu/dri' >> ~/.bashrc
fi

mkdir -p ~/.clipfusion
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install openai-whisper numpy pillow pyyaml --quiet
ok "Pacotes Python instalados"

python3 -c "import whisper" 2>/dev/null && ok "Whisper OK" || err "Whisper falhou"

cat > run.sh << 'RUNEOF'
#!/bin/bash
cd "$(dirname "$0")"
export LIBVA_DRIVER_NAME=iHD
export LIBVA_DRIVERS_PATH=/usr/lib/x86_64-linux-gnu/dri
source venv/bin/activate
python3 main.py
RUNEOF
chmod +x run.sh
ok "run.sh criado"

echo ""
echo "╔═════════════════════════════════════════╗"
echo "║  ✅ PRONTO — para iniciar:             ║"
echo "║     cd $INSTALL_DIR && ./run.sh        ║"
echo "╚═════════════════════════════════════════╝"
