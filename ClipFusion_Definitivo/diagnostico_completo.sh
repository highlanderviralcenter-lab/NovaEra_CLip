#!/bin/bash
# Diagnóstico completo do ClipFusion

LOG="diagnostico_$(date +%Y%m%d_%H%M%S).log"
echo "🔍 DIAGNÓSTICO CLIPFUSION - $(date)" | tee $LOG
echo "================================" | tee -a $LOG

# 1. Hardware
echo "" | tee -a $LOG
echo "💻 HARDWARE:" | tee -a $LOG
echo "CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)" | tee -a $LOG
echo "RAM: $(free -h | grep Mem | awk '{print $2}')" | tee -a $LOG
echo "ZRAM: $(swapon --show=NAME,SIZE | grep zram || echo 'Não ativo')" | tee -a $LOG
lspci | grep -i vga | tee -a $LOG

# 2. VA-API
echo "" | tee -a $LOG
echo "🎬 VA-API:" | tee -a $LOG
vainfo 2>&1 | head -20 | tee -a $LOG

# 3. Arquivos do projeto
echo "" | tee -a $LOG
echo "📁 ARQUIVOS:" | tee -a $LOG
ls -la core/cut_engine.py run.sh config.yaml 2>&1 | tee -a $LOG

# 4. Configuração atual
echo "" | tee -a $LOG
echo "⚙️  CONFIG:" | tee -a $LOG
cat config.yaml | tee -a $LOG

# 5. Teste de importação (com timeout)
echo "" | tee -a $LOG
echo "🧪 TESTE DE IMPORTAÇÃO:" | tee -a $LOG
timeout 10 python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from core.transcriber import WhisperTranscriber
    print('✅ WhisperTranscriber OK')
except Exception as e:
    print(f'❌ Whisper: {e}')
    
try:
    from core.cut_engine import render_cut
    print('✅ render_cut OK')
except Exception as e:
    print(f'❌ cut_engine: {e}')
    
try:
    from gui.main_gui import MainGUI
    print('✅ MainGUI OK')
except Exception as e:
    print(f'❌ MainGUI: {e}')
" 2>&1 | tee -a $LOG

# 6. Teste de memória disponível
echo "" | tee -a $LOG
echo "🧠 MEMÓRIA:" | tee -a $LOG
free -h | tee -a $LOG
echo "" | tee -a $LOG
echo "Processos Python rodando:" | tee -a $LOG
ps aux | grep python | grep -v grep | tee -a $LOG

# 7. Teste FFmpeg
echo "" | tee -a $LOG
echo "🎥 FFMPEG:" | tee -a $LOG
ffmpeg -version | head -3 | tee -a $LOG
echo "" | tee -a $LOG
echo "Codecs VA-API disponíveis:" | tee -a $LOG
ffmpeg -codecs 2>/dev/null | grep vaapi | tee -a $LOG

echo "" | tee -a $LOG
echo "================================" | tee -a $LOG
echo "📄 Relatório salvo em: $LOG" | tee -a $LOG
echo "Envie este arquivo para análise" | tee -a $LOG

# Mostra o caminho do log
echo ""
echo "📋 CAMINHO DO LOG:"
realpath $LOG
