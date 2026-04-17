from faster_whisper import WhisperModel


def fmt_time(sec):
    return f"{int(sec//60)}:{int(sec%60):02d}"


def transcribe(audio_path, model_size="tiny"):
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language="pt", beam_size=5)
        full_text = " ".join(seg.text for seg in segments)
        if not full_text.strip():
            return "[Transcrição vazia - áudio sem fala detectada?]"
        return full_text
    except Exception as e:
        return f"[Erro na transcrição: {str(e)}]"


class WhisperTranscriber:
    """Wrapper OO do faster-whisper. Retorna dict compatível com main_gui.py."""

    def __init__(self, model_size="tiny", model=None, device="cpu", compute_type="int8"):
        self.model_size = model if model is not None else model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, audio_path, language="pt", beam_size=5):
        """Retorna dict: {"full_text": str, "segments": [{"start", "end", "text"}]}"""
        try:
            model = self._load_model()
            raw_segments, _ = model.transcribe(
                audio_path, language=language, beam_size=beam_size
            )
            seg_list = [
                {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                for seg in raw_segments
            ]
            full_text = " ".join(s["text"] for s in seg_list)
            if not full_text.strip():
                full_text = "[Transcrição vazia - áudio sem fala detectada?]"
            return {"full_text": full_text, "segments": seg_list}
        except Exception as e:
            return {"full_text": f"[Erro na transcrição: {str(e)}]", "segments": []}
