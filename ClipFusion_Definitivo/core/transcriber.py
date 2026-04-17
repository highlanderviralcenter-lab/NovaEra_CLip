import gc
import os
import subprocess
from memory_manager import get_memory_manager


def fmt_time(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


class WhisperTranscriber:
    """
    Transcriber com seleção dinâmica de modelo:
    - default tiny
    - base se vídeo > 20min e RAM efetiva > 4GB
    - small apenas se vídeo > 60min, RAM > 6GB e confirmação explícita
    """

    def __init__(self, model="tiny", language="pt", device="cpu", compute_type="int8"):
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.user_model = model or "tiny"
        self._model = None
        self._model_name = None
        self.mm = get_memory_manager()

    def _video_minutes(self, video_path):
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(result.stdout.strip()) / 60.0
        except Exception:
            return 0.0

    def _choose_model(self, video_path, allow_small=False):
        mins = self._video_minutes(video_path)
        # Se usuário pediu tiny/base explicitamente, respeita (small continua protegido).
        if self.user_model in {"tiny", "base"}:
            return self.user_model
        return self.mm.recommend_whisper_model(mins, ask_small=allow_small)

    def _load_model(self, model_name):
        if self._model is not None and self._model_name != model_name:
            # Nunca manter dois modelos na RAM.
            self._model = None
            self._model_name = None
            gc.collect()

        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._model_name = model_name
        return self._model

    def transcribe(self, video_path, progress_callback=None, allow_small=False):
        if not os.path.exists(video_path):
            raise FileNotFoundError(video_path)

        if not self.mm.request_allocation(300, priority="normal"):
            raise RuntimeError("Memória insuficiente para iniciar transcrição.")

        try:
            model_name = self._choose_model(video_path, allow_small=allow_small)
            if progress_callback:
                progress_callback(f"🧠 Whisper model: {model_name}")
            model = self._load_model(model_name)

            segments_iter, _info = model.transcribe(
                video_path,
                language=self.language,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
            )

            segments = []
            texts = []
            for seg in segments_iter:
                text = (seg.text or "").strip()
                if not text:
                    continue
                segments.append({
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": text,
                })
                texts.append(text)

            full_text = " ".join(texts).strip()
            if not full_text:
                full_text = "[Transcrição vazia - áudio sem fala detectada?]"

            return {"full_text": full_text, "segments": segments, "model": model_name}
        finally:
            self.mm.release_allocation(300)
            gc.collect()
