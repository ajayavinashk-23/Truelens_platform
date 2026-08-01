"""
Loads all pretrained models exactly once and holds them in module-level
singletons. Detector services pull from here instead of calling
`from_pretrained` per-request.

Call `load_all_models()` once from the FastAPI startup event in app.py.
"""

import logging
import torch

logger = logging.getLogger("truelens.model_loader")

# Public model IDs (real, hosted on the Hugging Face Hub).
# Face-deepfake model: SigLIP2-based, Apache-2.0, documented unambiguous
# label convention (id2label: {"0": "fake", "1": "real"}) — see
# https://huggingface.co/prithivMLmods/deepfake-detector-model-v1
# Reported classification report: ~94.4% accuracy on its own eval set.
# Used ONLY when a face is detected in the image/frame.
IMAGE_MODEL_ID = "prithivMLmods/deepfake-detector-model-v1"  # SigLIP2, fine-tuned for deepfake detection

# General (non-face) AI-generated image detector: ConvNeXT-based binary
# classifier trained to separate AI-generated images (any subject —
# landscapes, art, objects, screenshots, animals, buildings...) from real
# photographs. Used whenever NO face is detected, since the face model
# above is trained/evaluated specifically on face-swap and face-synthesis
# data and is not the right tool for e.g. an AI-generated landscape.
# See https://huggingface.co/umm-maybe/AI-image-detector
GENERAL_IMAGE_MODEL_ID = "umm-maybe/AI-image-detector"

# Second, independently-trained face-deepfake classifier. Root-cause fix for
# the reported bug (AI faces predicted REAL): a single model's blind spots
# were being trusted outright. This is a different architecture/training set
# (ViT-based) from IMAGE_MODEL_ID above (SigLIP2-based) — see
# services/ensemble_engine.py and services/second_face_detector.py for how
# it's combined with everything else, never trusted alone either.
# https://huggingface.co/dima806/deepfake_vs_real_image_detection
SECOND_FACE_MODEL_ID = "dima806/deepfake_vs_real_image_detection"

AUDIO_MODEL_ID = "garystafford/wav2vec2-deepfake-voice-detector"  # Wav2Vec2, 0=real / 1=fake

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Make inference reproducible: same image in -> same numbers out, every
# time. Without this, cuDNN is allowed to auto-tune/benchmark and pick
# among several numerically-slightly-different (but faster) convolution
# algorithms, and can pick a different one from run to run — usually a
# harmless rounding difference, but close to a REAL/FAKE decision
# threshold it's enough to flip the verdict on an otherwise-identical
# upload. Also seeds torch's RNG in case any op (e.g. dropout, if a future
# model swap leaves training-mode layers behind) still depends on it.
torch.manual_seed(0)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

_state = {
    "image_model": None,
    "image_processor": None,
    "general_image_model": None,
    "general_image_processor": None,
    "general_image_available": False,
    "second_face_model": None,
    "second_face_processor": None,
    "second_face_available": False,
    "audio_model": None,
    "audio_feature_extractor": None,
    "loaded": False,
}


def load_all_models():
    """Idempotent. Loads image + general-image + audio models onto DEVICE once."""
    if _state["loaded"]:
        return

    logger.info("Loading pretrained models onto device=%s ...", DEVICE)

    from transformers import (
        AutoModelForImageClassification,
        AutoImageProcessor,
        AutoModelForAudioClassification,
        AutoFeatureExtractor,
    )

    # Auto* classes (not architecture-specific ViT classes) so swapping
    # IMAGE_MODEL_ID for a different checkpoint — ViT, SigLIP, ConvNeXT, or
    # anything else transformers supports for image classification — is a
    # one-line change here, nothing else in the codebase needs to know the
    # architecture.
    _state["image_processor"] = AutoImageProcessor.from_pretrained(IMAGE_MODEL_ID)
    image_model = AutoModelForImageClassification.from_pretrained(IMAGE_MODEL_ID)
    image_model.to(DEVICE).eval()
    _state["image_model"] = image_model

    # The general (non-face) detector is treated as a soft dependency: if
    # the configured model ID can't be fetched (e.g. offline dev, HF Hub
    # hiccup, model renamed/removed upstream) we log loudly and disable
    # only the no-face pipeline, rather than crashing the whole app and
    # taking the face pipeline down with it.
    try:
        _state["general_image_processor"] = AutoImageProcessor.from_pretrained(GENERAL_IMAGE_MODEL_ID)
        general_model = AutoModelForImageClassification.from_pretrained(GENERAL_IMAGE_MODEL_ID)
        general_model.to(DEVICE).eval()
        _state["general_image_model"] = general_model
        _state["general_image_available"] = True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Could not load general (non-face) AI image detector '%s'. "
            "Images/frames with no detected face will fall back to the "
            "face-deepfake model on the full frame, with a warning attached.",
            GENERAL_IMAGE_MODEL_ID,
        )
        _state["general_image_available"] = False

    # Same soft-dependency treatment as the general image detector: if this
    # second face model can't be fetched, the ensemble engine just runs
    # with one fewer vote and attaches a warning — it never takes the app
    # down, and the primary SigLIP2 face pipeline keeps working on its own.
    try:
        _state["second_face_processor"] = AutoImageProcessor.from_pretrained(SECOND_FACE_MODEL_ID)
        second_face_model = AutoModelForImageClassification.from_pretrained(SECOND_FACE_MODEL_ID)
        second_face_model.to(DEVICE).eval()
        _state["second_face_model"] = second_face_model
        _state["second_face_available"] = True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Could not load second face-deepfake detector '%s'. The face "
            "pipeline will fall back to running on the primary SigLIP2 "
            "model plus the non-model signals (ELA/frequency/noise) only.",
            SECOND_FACE_MODEL_ID,
        )
        _state["second_face_available"] = False

    _state["audio_feature_extractor"] = AutoFeatureExtractor.from_pretrained(AUDIO_MODEL_ID)
    audio_model = AutoModelForAudioClassification.from_pretrained(AUDIO_MODEL_ID)
    audio_model.to(DEVICE).eval()
    _state["audio_model"] = audio_model

    _state["loaded"] = True
    logger.info(
        "Model loading complete. general_image_available=%s second_face_available=%s",
        _state["general_image_available"], _state["second_face_available"],
    )


def get_image_model():
    if not _state["loaded"]:
        load_all_models()
    return _state["image_model"], _state["image_processor"]


def get_general_image_model():
    """@returns (model, processor) or (None, None) if unavailable."""
    if not _state["loaded"]:
        load_all_models()
    if not _state["general_image_available"]:
        return None, None
    return _state["general_image_model"], _state["general_image_processor"]


def get_second_face_model():
    """@returns (model, processor) or (None, None) if unavailable."""
    if not _state["loaded"]:
        load_all_models()
    if not _state["second_face_available"]:
        return None, None
    return _state["second_face_model"], _state["second_face_processor"]


def get_audio_model():
    if not _state["loaded"]:
        load_all_models()
    return _state["audio_model"], _state["audio_feature_extractor"]
