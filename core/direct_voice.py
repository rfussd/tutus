from __future__ import annotations

"""
Pipeline de voz directa Speech-to-Speech.
Entrada: audio o texto
Salida: audio generado localmente con SpeechT5 (GPU, sin internet)
"""
import logging
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch
from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Processor

log = logging.getLogger("tutus.direct_voice")


DATA_DIR: Path = Path(__file__).parent.parent / "data"
SPEAKER_EMBEDDING_PATH: Path = DATA_DIR / "speaker_embedding.pt"
_device: str = "cuda" if torch.cuda.is_available() else "cpu"

_tts_model: SpeechT5ForTextToSpeech | None = None
_tts_processor: SpeechT5Processor | None = None
_vocoder: SpeechT5HifiGan | None = None
_speaker_embedding: torch.Tensor | None = None
_s2s_thread: threading.Thread | None = None
_running: bool = False


def _ensure_tts() -> None:
    global _tts_model, _tts_processor, _vocoder, _speaker_embedding
    if _tts_model is not None:
        return

    log.info("[DirectVoice] Cargando SpeechT5 en %s...", _device)

    _tts_processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    _tts_model = SpeechT5ForTextToSpeech.from_pretrained(
        "microsoft/speecht5_tts",
        torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
    ).to(_device)  # type: ignore[arg-type]
    _vocoder = SpeechT5HifiGan.from_pretrained(
        "microsoft/speecht5_hifigan",
        torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
    ).to(_device)  # type: ignore[arg-type]

    if _device == "cuda":
        _tts_model = _tts_model.half()
        _vocoder = _vocoder.half()

    _tts_model.eval()
    _vocoder.eval()

    if SPEAKER_EMBEDDING_PATH.exists():
        _speaker_embedding = torch.load(SPEAKER_EMBEDDING_PATH, map_location=_device)
        log.info("[DirectVoice] Embedding de voz cargado")
    else:
        _speaker_embedding = torch.zeros(1, 512).to(_device)
        log.info("[DirectVoice] Sin clonacion de voz, usando voz por defecto")

    log.info("[DirectVoice] SpeechT5 listo en %s", _device)


def text_to_speech(text: str, output_path: str | None = None) -> np.ndarray | None:
    _ensure_tts()
    if not text or not text.strip():
        return None

    inputs = _tts_processor(text=text, return_tensors="pt").to(_device)  # type: ignore[misc]

    with torch.no_grad():
        speech = _tts_model.generate(  # type: ignore[union-attr]
            inputs["input_ids"],
            speaker_embeddings=_speaker_embedding,  # type: ignore[arg-type]
            vocoder=_vocoder,
        )

    audio = speech.cpu().numpy().squeeze()  # type: ignore[union-attr]

    if output_path:
        from scipy.io.wavfile import write as wav_write

        wav_write(output_path, 16000, (audio * 32767).astype(np.int16))

    return audio


def stream_text_to_speech(text: str, on_audio_chunk: Callable[[np.ndarray], None]) -> None:
    _ensure_tts()
    if not text or not text.strip():
        return

    sentences = text.replace("!", ".").replace("?", ".").replace("\n", " ").split(".")
    sentences = [s.strip() + "." for s in sentences if len(s.strip()) > 5]

    for sentence in sentences:
        try:
            audio = text_to_speech(sentence)
            if audio is not None:
                on_audio_chunk(audio)
        except Exception as e:
            log.error("[DirectVoice] Error en chunk: %s", e)


def clone_voice(audio_path: str) -> str:
    _ensure_tts()
    try:
        import librosa
        from transformers import SpeechT5ForSpeechToText
        from transformers import SpeechT5Processor as SttProcessor

        stt_model = SpeechT5ForSpeechToText.from_pretrained(
            "microsoft/speecht5_asr",
            torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
        ).to(_device)  # type: ignore[arg-type]
        stt_processor = SttProcessor.from_pretrained("microsoft/speecht5_asr")

        audio, sr = librosa.load(audio_path, sr=16000)
        audio = torch.from_numpy(audio).float()  # type: ignore[assignment]

        with torch.no_grad():
            inputs = stt_processor(audio, sampling_rate=16000, return_tensors="pt").to(_device)
            embedding = stt_model.encoder(inputs["input_values"])
            speaker_embedding = embedding.last_hidden_state.mean(dim=1)

        torch.save(speaker_embedding, SPEAKER_EMBEDDING_PATH)
        _speaker_embedding = speaker_embedding

        return f"Voz clonada desde: {audio_path}"
    except Exception as e:
        return f"Error clonando voz: {e}"


def record_and_clone(duration: int = 30) -> str:
    from scipy.io.wavfile import write as wav_write

    from core.listener import record_audio_raw

    log.info("[DirectVoice] Grabando %ss de tu voz...", duration)
    audio = record_audio_raw(duration)

    tmp_path = DATA_DIR / "voice_sample.wav"
    wav_write(str(tmp_path), 16000, audio)

    return clone_voice(str(tmp_path))


def has_cloned_voice() -> bool:
    return SPEAKER_EMBEDDING_PATH.exists()


def get_device() -> str:
    return _device
