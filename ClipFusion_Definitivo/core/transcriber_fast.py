from __future__ import annotations

import os
import subprocess
import tempfile
import gc


def fmt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h >= 1:
        return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"
    return f"{int(m):02d}:{s:05.2f}"


class FastWhisperTranscriber:
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _get_model(self):
        """Lazy loading - carrega modelo só quando necessário"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except Exception as e:
                raise RuntimeError(
                    "faster-whisper não instalado. Rode: pip install faster-whisper"
                ) from e
            
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=1,
                num_workers=1,
            )
        return self._model

    def _extract_audio_chunk(self, video_path: str, wav_path: str, start: float = 0, duration: float = None) -> None:
        """Extrai chunk de áudio do vídeo"""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
        ]
        if duration:
            cmd.extend(["-t", str(duration)])
        
        cmd.extend([
            "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            wav_path,
        ])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _get_audio_duration(self, video_path: str) -> float:
        """Pega duração do vídeo em segundos"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def transcribe(self, video_path: str, language: str = "pt", chunk_duration: float = 30.0):
        """Transcreve em chunks para economizar memória"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(video_path)

        total_duration = self._get_audio_duration(video_path)
        
        all_segments = []
        full_text_parts = []
        
        chunk_start = 0.0
        chunk_index = 0
        
        while chunk_start < total_duration:
            chunk_end = min(chunk_start + chunk_duration, total_duration)
            actual_duration = chunk_end - chunk_start
            
            print(f"Processando chunk {chunk_index + 1}: {chunk_start:.1f}s - {chunk_end:.1f}s")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                wav_path = os.path.join(tmpdir, "chunk.wav")
                
                self._extract_audio_chunk(video_path, wav_path, chunk_start, actual_duration + 1.0)
                
                model = self._get_model()
                segments_iter, info = model.transcribe(
                    wav_path,
                    language=language,
                    vad_filter=True,
                    beam_size=1,
                    best_of=1,
                    condition_on_previous_text=False,
                )
                
                for seg in segments_iter:
                    text = (seg.text or "").strip()
                    if not text:
                        continue
                    
                    global_start = chunk_start + float(seg.start)
                    global_end = chunk_start + float(seg.end)
                    
                    item = {
                        "start": global_start,
                        "end": global_end,
                        "text": text,
                    }
                    all_segments.append(item)
                    full_text_parts.append(text)
                
                del segments_iter
                gc.collect()
            
            chunk_start = chunk_end
            chunk_index += 1
            gc.collect()
        
        return {
            "text": " ".join(full_text_parts).strip(),
            "segments": all_segments,
            "engine": "faster_whisper",
            "language": language,
        }
