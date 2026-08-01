"""
Camera sensor noise-residual analysis.

Real photographs carry sensor noise (photon shot noise, read noise) whose
local variance differs meaningfully between flat regions (sky, skin,
out-of-focus background) and detailed/edge regions (hair, texture, fabric).
GAN and diffusion decoders tend to either over-smooth this away or leave a
noise pattern that's unnaturally *uniform* across the frame regardless of
local detail. This estimates a noise residual (image minus a denoised
version of itself) and scores how "natural" its regional variance pattern
looks — a cheap, deterministic, model-free signal used as one more
independent vote in services/ensemble_engine.py.
"""

import cv2
import numpy as np


def compute_noise_score(image_bgr: np.ndarray) -> dict:
    """
    @param image_bgr: OpenCV BGR image or face crop.
    @returns {
        "prob_real_noise": float,  # 0-1, this signal's own opinion
        "noise_score": float,      # 0-1 raw anomaly score (higher = more likely over-smoothed/synthetic)
    }
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    if gray.shape[0] < 16 or gray.shape[1] < 16:
        return {"prob_real_noise": 0.5, "noise_score": 0.0}

    denoised = cv2.fastNlMeansDenoising(gray, h=7)
    residual = gray.astype(np.float32) - denoised.astype(np.float32)

    h, w = residual.shape
    grid_y, grid_x = 6, 6
    patch_vars = []
    for i in range(grid_y):
        for j in range(grid_x):
            y0, y1 = int(i * h / grid_y), int((i + 1) * h / grid_y)
            x0, x1 = int(j * w / grid_x), int((j + 1) * w / grid_x)
            patch = residual[y0:y1, x0:x1]
            if patch.size > 4:
                patch_vars.append(float(patch.var()))

    if not patch_vars:
        return {"prob_real_noise": 0.5, "noise_score": 0.0}

    mean_var = float(np.mean(patch_vars))
    std_var = float(np.std(patch_vars))
    # Coefficient of variation across regions: natural photos vary
    # noticeably; over-smoothed synthetic output tends toward near-zero
    # variation (every patch looks about equally "clean").
    cv_ratio = std_var / mean_var if mean_var > 1e-6 else 0.0

    too_smooth_overall = max(0.0, 1.0 - mean_var / 6.0)
    too_uniform_across_regions = max(0.0, 1.0 - cv_ratio / 1.2)
    noise_score = float(max(0.0, min(1.0, 0.6 * too_smooth_overall + 0.4 * too_uniform_across_regions)))

    return {"prob_real_noise": round(1.0 - noise_score, 4), "noise_score": round(noise_score, 4)}
