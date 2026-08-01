"""
Hybrid-ish audio-authenticity pipeline (single model — Wav2Vec2 deepfake
voice detector — but now with real preprocessing and windowed inference
instead of one forward pass over the raw clip):

  1. Load + resample to 16kHz mono.
  2. Voice-activity detection / silence trimming, noise reduction, and
     loudness normalization (utils/audio_dsp.py).
  3. Split into overlapping windows so a short synthetic splice inside a
     long, mostly-genuine recording isn't averaged away by the rest of
     the clip.
  4. Run inference on every window independently.
  5. Aggregate: overall probability + the specific windows (segments)
     flagged as suspicious, with their timestamps.
"""

import io
import logging

import librosa
import numpy as np
import torch

from services.model_loader import get_audio_model, DEVICE
from utils.audio_dsp import assess_audio_quality, normalize_loudness, reduce_noise, trim_silence

logger = logging.getLogger("truelens.audio_detector")

TARGET_SAMPLE_RATE = 16000
WINDOW_SECONDS = 4.0
HOP_SECONDS = 2.0  # 50% overlap
MIN_WINDOW_SECONDS = 1.0  # shorter trailing windows below this are dropped, not padded-and-scored


def _resolve_real_label_index(id2label: dict) -> int:
    for idx, label in id2label.items():
        lower = label.lower()
        if "real" in lower or "bonafide" in lower or "genuine" in lower:
            return int(idx)
    return 0  # documented convention for this model: 0=real, 1=fake


def _windows(y: np.ndarray, sr: int):
    window_len = int(WINDOW_SECONDS * sr)
    hop_len = int(HOP_SECONDS * sr)
    min_len = int(MIN_WINDOW_SECONDS * sr)

    if len(y) <= window_len:
        if len(y) >= min_len:
            yield 0.0, len(y) / sr, y
        return

    start = 0
    while start < len(y):
        end = min(start + window_len, len(y))
        segment = y[start:end]
        if len(segment) >= min_len:
            yield start / sr, end / sr, segment
        if end == len(y):
            break
        start += hop_len


def predict_audio_bytes(audio_bytes: bytes) -> dict:
    """
    @returns {
        "prob_real": float,           # overall, weighted average across segments
        "segments": [{"start": float, "end": float, "prob_real": float, "deepfake_probability": float}, ...],
        "suspicious_segments": [...],  # subset of segments with deepfake_probability > 50
        "quality": {...},
        "quality_factor": float,       # 0-1, fed into confidence calibration
        "warnings": [str, ...],
    }
    """
    model, feature_extractor = get_audio_model()
    real_idx = _resolve_real_label_index(model.config.id2label)

    raw_audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=TARGET_SAMPLE_RATE, mono=True)
    original_duration_s = len(raw_audio) / sr if sr else 0.0
    if original_duration_s <= 0:
        raise ValueError("Could not decode the uploaded audio — it may be corrupted or in an unsupported format.")

    quality = assess_audio_quality(raw_audio, sr, original_duration_s)

    cleaned = trim_silence(raw_audio, sr)
    if cleaned.size == 0:
        raise ValueError("Audio contains no detectable speech (entirely silent).")
    cleaned = reduce_noise(cleaned)
    cleaned = normalize_loudness(cleaned)

    segments = []
    warnings = list(quality["warnings"])

    for start_s, end_s, segment in _windows(cleaned, sr):
        inputs = feature_extractor(segment, sampling_rate=sr, return_tensors="pt", padding=True)
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze()
        prob_real = probs[real_idx].item() if probs.dim() > 0 else probs.item()
        deepfake_probability = round((1 - prob_real) * 100, 1)
        segments.append(
            {
                "start": round(start_s, 2),
                "end": round(end_s, 2),
                "prob_real": round(prob_real, 4),
                "deepfake_probability": deepfake_probability,
            }
        )

    if not segments:
        raise ValueError("Audio clip is too short after silence trimming to analyze.")

    # Weight each segment by its duration so a trailing short window
    # doesn't count equally against a full-length one.
    total_duration = sum(s["end"] - s["start"] for s in segments) or 1.0
    prob_real = sum(s["prob_real"] * (s["end"] - s["start"]) for s in segments) / total_duration

    suspicious_segments = [s for s in segments if s["deepfake_probability"] > 50]

    quality_factor = min(1.0, quality["quality_score"] / 100.0) if quality["quality_score"] else 0.3
    if len(segments) == 1:
        # A single short window carries less aggregate evidence than
        # many overlapping windows agreeing with each other.
        quality_factor = min(quality_factor, 0.85)

    logger.info(
        "audio segments=%d prob_real=%.4f duration=%.1fs quality_score=%s",
        len(segments), prob_real, original_duration_s, quality["quality_score"],
    )

    return {
        "prob_real": prob_real,
        "segments": segments,
        "suspicious_segments": suspicious_segments,
        "quality": quality,
        "quality_factor": quality_factor,
        "warnings": warnings,
    }
