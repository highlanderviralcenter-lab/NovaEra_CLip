#!/bin/bash
# conserta_tudo.sh - Reseta e corrige o ClipFusion de uma vez

set -e

cd ~/clipfusionV2

echo "🔧 Passo 1: Destruindo ambiente virtual antigo e recriando..."
deactivate 2>/dev/null || true
rm -rf venv
python3 -m venv venv

echo "🔧 Passo 2: Ativando o novo ambiente virtual..."
source venv/bin/activate

echo "🔧 Passo 3: Instalando pip atualizado e dependências..."
venv/bin/pip install --upgrade pip
venv/bin/pip install faster-whisper numpy pillow pyyaml sqlalchemy

echo "🔧 Passo 4: Verificando instalação do faster-whisper..."
python -c "from faster_whisper import WhisperModel; print('✅ faster-whisper OK')"

echo "🔧 Passo 5: Garantindo que os arquivos principais têm as correções..."

# main_gui.py (com métodos _lbl, _btn, etc.)
cat > gui/main_gui.py << 'PY'
[COLE AQUI O CÓDIGO DO main_gui.py QUE VOCÊ JÁ TEM OU USE O DA MINHA MENSAGEM ANTERIOR]
PY

# decision_engine.py (com a classe DecisionEngine)
cat > core/decision_engine.py << 'PY'
class DecisionEngine:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {'approved': 9.0, 'rework': 7.0, 'discard': 0.0}

    def decide(self, local_score, ai_score=None, platform_fit=0.0, trans_quality=0.0):
        if ai_score is None:
            final_score = round(float(local_score), 2)
            if final_score >= self.thresholds['approved']:
                return 'approved', f"Score local alto ({final_score:.2f})"
            elif final_score >= self.thresholds['rework']:
                return 'retry', f"Score local médio ({final_score:.2f})"
            else:
                return 'rejected', f"Score local baixo ({final_score:.2f})"
        final_score = (float(local_score)*0.5 + float(ai_score)*0.3 + float(platform_fit)*0.1 + float(trans_quality)*0.1)
        final_score = round(final_score, 2)
        if final_score >= self.thresholds['approved']:
            return 'approved', f"Final {final_score:.2f}"
        elif final_score >= self.thresholds['rework']:
            return 'retry', f"Final {final_score:.2f}"
        else:
            return 'rejected', f"Final {final_score:.2f}"
PY

# db.py com a função ensure_scores_schema (se necessário)
python -c "import db; db.init_db(); print('✅ Banco OK')"

echo "🔧 Passo 6: Testando a interface..."
python -c "from gui.main_gui import ClipFusionApp; app = ClipFusionApp(); app.root.after(100, app.root.quit); app.run(); print('✅ Interface OK')"

echo "🎉 Pronto! Agora execute: python main.py"
