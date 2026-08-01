"""
Error Level Analysis (ELA).

Recompresses the image at a fixed, known JPEG quality and measures how
much each region's pixels shift relative to that recompression. Regions
already sitting near that compression level barely move; regions that were
pasted in, generated, or otherwise disturbed after the image's last real
compression pass shift by a different — and often patchier — amount than
the rest of the frame. This is a standard, deterministic manipulation-
forensics heuristic (no model weights, no training), used here as one more
independent vote in services/ensemble_engine.py so no single classifier's
opinion ever decides the result alone.
"""

import base64
import io

import cv2
import numpy as np
from PIL import Image

ELA_QUALITY = 90

# Empirically-reasonable scaling constant to map the raw mean recompression
# delta (0-255 pixel-value scale) into a 0-1 anomaly score. This is a
# heuristic scale factor, not a value calibrated against a labeled dataset —
# treat compute_ela()'s output as a supporting signal, not a verdict.
_ELA_SCALE = 18.0
_HEATMAP_GAIN = 6.0  # visual amplification only, does not affect the score


def compute_ela(image_bgr: np.ndarray) -> dict:
    """
    @param image_bgr: OpenCV BGR image or face crop.
    @returns {
        "prob_real_ela": float,        # 0-1, this signal's own opinion
        "manipulation_score": float,   # 0-1 raw anomaly score (higher = more suspicious)
        "heatmap_data_uri": str|None,  # base64 PNG, for the frontend's ELA panel
    }
    """
    ok, encoded = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), ELA_QUALITY])
    if not ok:
        return {"prob_real_ela": 0.5, "manipulation_score": 0.0, "heatmap_data_uri": None}

    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if recompressed is None or recompressed.shape != image_bgr.shape:
        return {"prob_real_ela": 0.5, "manipulation_score": 0.0, "heatmap_data_uri": None}

    diff = cv2.absdiff(image_bgr, recompressed).astype(np.float32)
    diff_gray = diff.mean(axis=2)

    mean_diff = float(diff_gray.mean())
    std_diff = float(diff_gray.std())

    # Patchiness: coarse 8x8 grid, look at the spread of per-patch means.
    # Real, single-source photos tend toward a fairly uniform ELA response
    # across the frame; spliced or locally-synthesized regions show up as
    # patches that differ sharply from their neighbors.
    h, w = diff_gray.shape
    grid_y, grid_x = 8, 8
    patch_means = []
    for i in range(grid_y):
        for j in range(grid_x):
            y0, y1 = int(i * h / grid_y), int((i + 1) * h / grid_y)
            x0, x1 = int(j * w / grid_x), int((j + 1) * w / grid_x)
            patch = diff_gray[y0:y1, x0:x1]
            if patch.size:
                patch_means.append(float(patch.mean()))
    patch_spread = float(np.std(patch_means)) if patch_means else 0.0

    raw_score = (mean_diff + 0.5 * std_diff + patch_spread) / _ELA_SCALE
    manipulation_score = float(max(0.0, min(1.0, raw_score)))
    prob_real_ela = round(1.0 - manipulation_score, 4)

    heatmap_uint8 = np.uint8(np.clip(diff_gray * _HEATMAP_GAIN, 0, 255))
    heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_INFERNO)
    heatmap_color_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)

    buf = io.BytesIO()
    Image.fromarray(heatmap_color_rgb).save(buf, format="PNG")
    heatmap_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "prob_real_ela": prob_real_ela,
        "manipulation_score": round(manipulation_score, 4),
        "heatmap_data_uri": heatmap_uri,
    }
