"""
Lightweight frequency-domain artifact heuristic.

Why this exists
----------------
The reported bug is that many AI-generated (particularly diffusion-
generated) faces are predicted REAL. The single-model face pipeline
(services/image_detector.py) previously trusted the SigLIP2 deepfake
model's softmax output on its own — one model, one vote, no cross-check.
GAN/diffusion upsampling (transposed-conv checkerboarding, or the
denoising process's tendency to over-smooth high-frequency camera-sensor
noise) tends to leave a statistically detectable fingerprint in the 2D
frequency spectrum that is largely independent of what a spatial-domain
classifier like SigLIP2 looks at. This doesn't require training or
downloading another model — it's a cheap, deterministic signal (a few
FFT calls) that gives image_detector.py a second, independent opinion to
weigh against the model's, per the "never let one model decide" goal,
without pulling in a full second deep-learning model.

This is a heuristic, not a trained classifier — treat its output as a
supporting signal (see FREQ_WEIGHT / DISAGREEMENT_THRESHOLD in
services/image_detector.py), not a standalone verdict.
"""

import cv2
import numpy as np

_FFT_SIZE = 256  # fixed size so scores are comparable across crop sizes
_RADIAL_BINS = 64


def _radial_power_spectrum(gray: np.ndarray) -> np.ndarray:
    resized = cv2.resize(gray, (_FFT_SIZE, _FFT_SIZE), interpolation=cv2.INTER_AREA).astype(np.float64)
    # Window to reduce edge-discontinuity spectral leakage.
    window = np.hanning(_FFT_SIZE)
    windowed = resized * window[:, None] * window[None, :]

    f = np.fft.fftshift(np.fft.fft2(windowed))
    power = np.abs(f) ** 2

    cy, cx = _FFT_SIZE // 2, _FFT_SIZE // 2
    y, x = np.indices(power.shape)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.int32)
    max_r = min(cx, cy)

    radial = np.zeros(_RADIAL_BINS)
    bin_edges = np.linspace(0, max_r, _RADIAL_BINS + 1)
    for i in range(_RADIAL_BINS):
        mask = (r >= bin_edges[i]) & (r < bin_edges[i + 1])
        if mask.any():
            radial[i] = power[mask].mean()
    return radial


def compute_frequency_artifact_score(crop_bgr: np.ndarray) -> dict:
    """
    @returns {
        "prob_real_freq": float,   # 0-1, this signal's own opinion (soft, deliberately not extreme)
        "anomaly_score": float,    # 0-1, raw artifact strength before dampening
        "reason": str|None,        # short human-readable note when the signal fired, else None
    }
    """
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    radial = _radial_power_spectrum(gray)

    radial_log = np.log1p(radial)
    total = radial_log.sum()
    if total <= 0:
        return {"prob_real_freq": 0.5, "anomaly_score": 0.0, "reason": None}

    # 1) Natural photos: power spectrum falls off roughly monotonically
    #    with frequency (1/f-ish). GAN/diffusion upsampling frequently
    #    produces a mid/high-frequency "bump" instead of a smooth
    #    falloff — periodic checkerboarding or denoiser over-smoothing
    #    followed by a sharpening pass. Measure this as: energy in the
    #    outer third of the spectrum vs a monotonic-falloff expectation.
    mid_high = radial_log[_RADIAL_BINS // 3:]
    diffs = np.diff(mid_high)
    # A natural falloff has mostly-negative (decreasing) successive
    # differences; a spike/bump shows up as positive jumps late in the
    # spectrum. Fraction of positive jumps in the outer band is our
    # "unnatural bump" signal.
    if len(diffs) > 0:
        bump_ratio = float((diffs > 0).sum()) / len(diffs)
    else:
        bump_ratio = 0.0

    # 2) Periodicity: a strong, narrow peak anywhere in the radial
    #    profile (as opposed to smooth energy) is characteristic of
    #    regular upsampling-grid artifacts. Peakiness ~ (max-mean)/std.
    std = radial_log.std()
    peakiness = float((radial_log.max() - radial_log.mean()) / std) if std > 1e-6 else 0.0
    peak_signal = min(1.0, max(0.0, (peakiness - 3.0) / 4.0))  # 0 until clearly spiky

    anomaly_score = min(1.0, 0.6 * max(0.0, bump_ratio - 0.35) / 0.65 + 0.4 * peak_signal)

    # Deliberately dampened: this heuristic is a supporting vote, not a
    # verdict, so it's never allowed to swing all the way to 0 or 1 on
    # its own — clip to [0.15, 0.85] so it nudges the ensemble rather
    # than dominating it.
    prob_real_freq = max(0.15, min(0.85, 1.0 - anomaly_score))

    reason = None
    if anomaly_score > 0.5:
        reason = "Frequency-spectrum analysis found unnatural high-frequency energy patterns atypical of camera-sensor noise."

    return {
        "prob_real_freq": round(prob_real_freq, 4),
        "anomaly_score": round(anomaly_score, 4),
        "reason": reason,
    }
