# Guia de Instalação Debian para ClipFusionV1

Este guia descreve o processo para instalar e executar o ClipFusionV1
em um notebook com Debian ou distribuição compatível (Ubuntu, etc.).

## Pré‑requisitos

- Usuário com permissões de sudo para instalar pacotes (apenas se você
  desejar instalar `ffmpeg` ou `python3` via gerenciador de pacotes; caso
  já estejam disponíveis, sudo não é necessário).
- Processador Intel i5‑6200U (Skylake) ou superior recomendado.
- Pelo menos 8GB de RAM e 1GB de espaço em disco livre.
- Acesso à internet opcional; o instalador não depende de downloads via
  rede, mas você pode precisar para obter o código-fonte ou instalar
  `ffmpeg` caso ainda não esteja instalado.

## Passos de Instalação

1. **Obter o código:** clone ou copie o repositório contendo o
   diretório `ClipFusionV1/` para sua máquina.
2. **Tornar o instalador executável:**
   ```bash
   cd ClipFusionV1
   chmod +x FULLinstallClipFusionV1.sh
   ```
3. **Executar o instalador completo:**
   ```bash
   ./FULLinstallClipFusionV1.sh
   ```
   Este script irá:
   - Atualizar o sistema (passo opcional) e verificar dependências básicas
     como `python3` e `ffmpeg`.
   - Não instala dependências Python adicionais, pois o projeto utiliza
     apenas bibliotecas da biblioteca padrão.
   - Executar uma verificação preflight de ambiente (ffmpeg, espaço
     em disco, permissões).
   - Criar um vídeo de exemplo e realizar um smoke test no pipeline.
   - Gerar um relatório em `output/reports/install_report.md`.

4. **Utilização básica via CLI:**
   - Para processar um único vídeo:
     ```bash
     ./run/run.sh process --input /caminho/para/video.mp4 --name "MeuProjeto" --protection basic
     ```
   - Para enfileirar múltiplos vídeos:
     ```bash
     ./run/run.sh enqueue /caminho/um.mp4 /caminho/dois.mp4 --protection anti_ia
     ./run/run.sh run_queue
     ```

5. **Utilização da GUI:**
   - Execute:
     ```bash
     python3 -m ClipFusionV1.gui.main
     ```
   - Uma janela com abas será aberta.  Na aba **Projeto**, selecione um
     arquivo .mp4, escolha um nível de proteção e clique em **Iniciar**.

## Observações

- A biblioteca de transcrição Whisper é opcional.  Caso não esteja
  instalada, o sistema utilizará uma transcrição fictícia.
- Para habilitar o suporte a GPU na codificação VA‑API, verifique os
  parâmetros de kernel (`i915.enable_guc=3`) conforme descrito nos
  documentos técnicos.
