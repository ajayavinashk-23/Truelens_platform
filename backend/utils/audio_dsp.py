"""
Audio preprocessing shared by services/audio_detector.py: voice-activity
detection / silence trimming, light noise reduction, and loudness
normalization. Deliberately dependency-light (librosa + numpy/scipy only,
already in requirements.txt) rather than pulling in a separate VAD model —
these are all classic, well-understood signal-processing techniques and
don't need a neural model to do well enough as a preprocessing gate ahead
of the actual (neural) deepfake-voice classifier.
"""

import logging

import librosa
import numpy as np
from scipy.signal import wiener

logger = logging.getLogger("truelens.audio_dsp")


def voiced_intervals(y: np.ndarray, sr: int, top_db: float = 30.0):
    """
    Energy-based voice-activity detection via librosa's frame-RMS silence
    splitter. @returns Nx2 array of [start_sample, end_sample] intervals
    that are NOT silence. Empty array if the whole clip is silence.
    """
    if y.size == 0:
        return np.empty((0, 2), dtype=int)
    return librosa.effects.split(y, top_db=top_db)


def trim_silence(y: np.ndarray, sr: int, top_db: float = 30.0) -> np.ndarray:
    """Removes leading/trailing silence, and collapses interior silence
    gaps by concatenating voiced intervals — long silent stretches in the
    middle of a clip otherwise dilute the windowed segments computed
    downstream with content the model can't say anything about."""
    intervals = voiced_intervals(y, sr, top_db=top_db)
    if len(intervals) == 0:
        return y  # entirely silent/uniform; let the caller's quality check flag it
    chunks = [y[start:end] for start, end in intervals]
    return np.concatenate(chunks)


def reduce_noise(y: np.ndarray) -> np.ndarray:
    """Light denoising via a Wiener filter. This is a general-purpose
    adaptive noise-reduction filter (not tuned to any particular noise
    profile) — enough to knock down steady background hiss/hum before
    the classifier sees the signal, without the complexity/dependency
    weight of a full spectral-subtraction pipeline."""
    if y.size < 32:
        return y
    try:
        return wiener(y).astype(np.float32)
    except Exception:  # noqa: BLE001
        logger.warning("Wiener noise reduction failed; continuing with the original signal.", exc_info=True)
        return y


def normalize_loudness(y: np.ndarray, target_dbfs: float = -20.0) -> np.ndarray:
    """RMS-based loudness normalization to a target dBFS, with peak
    clipping guard. Puts clips recorded at wildly different volumes on a
    comparable footing before inference, since the classifier was trained
    at some particular loudness distribution."""
    rms = float(np.sqrt(np.mean(np.square(y)))) if y.size else 0.0
    if rms < 1e-6:
        return y
    current_dbfs = 20 * np.log10(rms)
    gain_db = target_dbfs - current_dbfs
    gain = 10 ** (gain_db / 20)
    y_norm = y * gain
    return np.clip(y_norm, -1.0, 1.0).astype(np.float32)


def assess_audio_quality(y: np.ndarray, sr: int, original_duration_s: float) -> dict:
    """Cheap quality signals surfaced in the API response and fed into
    confidence calibration, analogous to utils/image_quality.py."""
    warnings = []
    voiced = voiced_intervals(y, sr)
    voiced_duration_s = sum((end - start) for start, end in voiced) / sr if len(voiced) else 0.0
    voiced_ratio = voiced_duration_s / original_duration_s if original_duration_s > 0 else 0.0

    if original_duration_s < 1.0:
        warnings.append("Audio clip is very short — results may be less reliable.")
    if voiced_ratio < 0.15:
        warnings.append("Audio is mostly silence — very little speech was available to analyze.")

    rms = float(np.sqrt(np.mean(np.square(y)))) if y.size else 0.0
    quality_score = round(min(1.0, voiced_ratio * 1.3) * min(1.0, max(rms, 1e-4) * 20) * 100, 1)

    return {
        "duration_s": round(original_duration_s, 2),
        "voiced_ratio": round(voiced_ratio, 3),
        "quality_score": quality_score,
        "warnings": warnings,
    }
