"""
Explainability heatmaps for the image pipeline.

Both the face model (SigLIP2) and the general model (ConvNeXT-family) are
transformer/patch-based vision backbones, not classic CNNs with a single
final conv feature map — so the textbook Grad-CAM recipe (hook the last
conv layer) doesn't directly apply. This module implements the patch-token
generalization of the same idea, sometimes called "transformer attribution"
or "Grad-CAM on patch embeddings":

1. Hook the last transformer block's output hidden states (one vector per
   image patch, in a NxD tensor).
2. Backprop the predicted class logit to get a gradient for every patch
   token.
3. Weight each patch's activation vector by its (mean) gradient and sum
   across the feature dimension — the same "gradient-weighted activation"
   idea as classic Grad-CAM, just operating on patch tokens instead of
   conv spatial cells.
4. Reshape the per-patch scores back into their original grid layout,
   upsample to the image's pixel size, and colorize.

The encoder-layer list is located generically (search the model for the
largest torch.nn.ModuleList, which is reliably the transformer's stack of
blocks for both ViT/SigLIP and ConvNeXT-style stage blocks) rather than
hardcoding an attribute path — that keeps this working if IMAGE_MODEL_ID
or GENERAL_IMAGE_MODEL_ID in model_loader.py is swapped for a different
checkpoint later, per the module_loader docstring's stated goal of
one-line model swaps.

If the target architecture doesn't fit this pattern (irregular patch
grid, no discoverable ModuleList, etc.) this degrades gracefully and
returns None — the caller (services/image_detector.py) always has a
text-only explanation as a fallback, so a failed heatmap never blocks the
rest of the response.
"""

import base64
import io
import logging
import threading

import cv2
import numpy as np
import torch
from PIL import Image

logger = logging.getLogger("truelens.gradcam")

# The image/general models are shared, process-wide singletons (see
# services/model_loader.py). Grad-CAM temporarily registers hooks and runs
# a backward() pass on that same shared model — if two requests did this
# concurrently on different input images, one request's hooks could
# capture the other's activations/gradients, silently corrupting the
# explanation (and, if a stray .grad ever leaked into a later forward
# pass, potentially the prediction too). Serializing here keeps the
# shared model safe to use across concurrent requests.
_gradcam_lock = threading.Lock()


def _find_last_transformer_layer(model):
    """Heuristic: the transformer's stack of blocks is, in every
    architecture we target here, the largest torch.nn.ModuleList in the
    model. Returns the last module in that list, or None if none found."""
    candidates = []
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.ModuleList) and len(module) > 1:
            candidates.append((name, module))
    if not candidates:
        return None
    candidates.sort(key=lambda nm: len(nm[1]))
    _, module_list = candidates[-1]
    return module_list[-1]


def _to_data_uri(img_rgb: np.ndarray) -> str:
    pil_img = Image.fromarray(img_rgb.astype(np.uint8))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def generate_gradcam(model, processor, pil_image: Image.Image, target_idx: int, device: str):
    """
    @param pil_image: RGB PIL image, already cropped/preprocessed the same
        way it will be for the real prediction (e.g. the face crop)
    @param target_idx: class index to explain (the predicted class)
    @returns {"heatmap": data-uri PNG, "overlay": data-uri PNG} or None if
             this architecture/inputs don't support the technique.
    """
    last_layer = _find_last_transformer_layer(model)
    if last_layer is None:
        return None

    activations = {}
    gradients = {}

    def fwd_hook(_module, _inp, out):
        activations["value"] = out[0] if isinstance(out, tuple) else out

    def bwd_hook(_module, _grad_in, grad_out):
        gradients["value"] = grad_out[0]

    _gradcam_lock.acquire()
    handle_fwd = last_layer.register_forward_hook(fwd_hook)
    handle_bwd = last_layer.register_full_backward_hook(bwd_hook)

    try:
        model.zero_grad(set_to_none=True)
        inputs = processor(images=pil_image, return_tensors="pt").to(device)
        outputs = model(**inputs)
        logits = outputs.logits
        score = logits[0, target_idx]
        score.backward()

        if "value" not in activations or "value" not in gradients:
            return None

        acts = activations["value"][0].detach()   # (tokens, hidden) or (H, W, C)-ish
        grads = gradients["value"][0].detach()

        if acts.dim() != 2:
            # Non patch-token architecture (e.g. pure conv stage output);
            # not supported by this generalized implementation.
            return None

        weights = grads.mean(dim=0)                        # (hidden,)
        cam = torch.relu((acts * weights).sum(dim=-1))      # (tokens,)
        tokens = cam.cpu().numpy()

        n = tokens.shape[0]
        side = int(round(n ** 0.5))
        if side * side != n and side * side == n - 1:
            # Leading CLS-style token present — drop it.
            tokens = tokens[1:]
            n -= 1
            side = int(round(n ** 0.5))
        if side * side != n or side < 2:
            return None

        grid = tokens.reshape(side, side)
        grid = grid - grid.min()
        if grid.max() > 1e-8:
            grid = grid / grid.max()

        img_np = np.array(pil_image.convert("RGB"))
        h, w = img_np.shape[:2]
        heatmap = cv2.resize(grid.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        heatmap = np.clip(heatmap, 0, 1)
        heatmap_uint8 = np.uint8(255 * heatmap)
        heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        heatmap_color_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)

        overlay = cv2.addWeighted(img_np.astype(np.uint8), 0.55, heatmap_color_rgb, 0.45, 0)

        return {
            "original": _to_data_uri(img_np),
            "heatmap": _to_data_uri(heatmap_color_rgb),
            "overlay": _to_data_uri(overlay),
            "top_region": _dominant_region(grid),
        }
    except Exception:  # noqa: BLE001
        logger.warning("Grad-CAM generation failed; continuing without a heatmap.", exc_info=True)
        return None
    finally:
        handle_fwd.remove()
        handle_bwd.remove()
        model.zero_grad(set_to_none=True)
        _gradcam_lock.release()


def _dominant_region(grid: np.ndarray) -> str:
    """Coarse human-readable location of the strongest activation, used to
    generate a sentence like 'concentrated around the eyes/upper-face'
    without needing real facial landmark detection."""
    side = grid.shape[0]
    y, x = np.unravel_index(np.argmax(grid), grid.shape)
    vertical = "upper" if y < side / 3 else ("lower" if y > 2 * side / 3 else "middle")
    horizontal = "left" if x < side / 3 else ("right" if x > 2 * side / 3 else "center")
    if vertical == "middle" and horizontal == "center":
        return "central region"
    return f"{vertical}-{horizontal} region"
