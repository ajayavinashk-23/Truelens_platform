"""
Runs a non-face image (landscape, artwork, animal, building, product,
screenshot, document, logo, anime, ...) through the general AI-image
detector configured in model_loader.py (GENERAL_IMAGE_MODEL_ID). This is
the pipeline services/image_detector.py routes to whenever
utils/face_detection.py finds no face — the face-deepfake model
(prithivMLmods/deepfake-detector-model-v1) is trained specifically on
face-swap/face-synthesis data and isn't the right tool for judging
whether, say, an AI-generated mountain photo is synthetic.

Same "resolve which class index means real" pattern as
services/image_detector.py, generalized here to also look for the
AI-generation-specific vocabulary ("artificial", "synthetic", "generated",
"fake") this model family tends to use in its labels, in addition to
"real"/"authentic".
"""

import os
import logging

import cv2
import numpy as np
import torch
from PIL import Image

from services.model_loader import get_general_image_model, DEVICE

logger = logging.getLogger("truelens.general_image_detector")

_REAL_LABEL_OVERRIDE = os.getenv("GENERAL_IMAGE_REAL_LABEL_INDEX")

_REAL_HINTS = ("real", "authentic", "human", "natural", "photo")
_FAKE_HINTS = ("fake", "artificial", "synthetic", "generated", "ai", "gan", "diffusion")


def _resolve_real_label_index(id2label: dict) -> int:
    if _REAL_LABEL_OVERRIDE is not None:
        return int(_REAL_LABEL_OVERRIDE)

    for idx, label in id2label.items():
        lower = label.lower()
        if any(hint in lower for hint in _REAL_HINTS):
            return int(idx)

    # No "real"-ish label text found — infer by elimination: if exactly
    # one label matches the "fake" vocabulary, the other index is "real".
    fake_idx = None
    for idx, label in id2label.items():
        if any(hint in label.lower() for hint in _FAKE_HINTS):
            fake_idx = int(idx)
    if fake_idx is not None and len(id2label) == 2:
        other = [int(i) for i in id2label if int(i) != fake_idx]
        if other:
            return other[0]

    logger.warning(
        "Could not confidently resolve the 'real' label index for the general "
        "image detector (id2label=%s). Defaulting to index 0 — verify with "
        "GENERAL_IMAGE_REAL_LABEL_INDEX if results look inverted.",
        id2label,
    )
    return 0


def is_available() -> bool:
    model, _ = get_general_image_model()
    return model is not None


def predict_frame_bgr(frame_bgr: np.ndarray) -> dict:
    """
    @returns {"prob_real": float, "available": bool}
    If the general model failed to load, returns prob_real=0.5
    (maximally uncertain) with available=False so callers can attach a
    warning instead of presenting a fabricated confident result.
    """
    model, processor = get_general_image_model()
    if model is None:
        return {"prob_real": 0.5, "available": False}

    region_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(region_rgb)
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1).squeeze()

    real_idx = _resolve_real_label_index(model.config.id2label)
    prob_real = probs[real_idx].item()
    logger.debug(
        "general detector prob_real=%.4f (real_idx=%s, labels=%s)",
        prob_real, real_idx, model.config.id2label,
    )
    return {"prob_real": prob_real, "available": True}
