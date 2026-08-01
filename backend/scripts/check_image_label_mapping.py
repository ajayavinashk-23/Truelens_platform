"""
Diagnostic script: verifies which output index of the configured image
deepfake detector actually means "real".

Why this exists
----------------
Label-mapping bugs (a model's config.json id2label not matching how it
was actually trained) are a real, recurring issue across community model
checkpoints — the previously-used Deep-Fake-Detector-v2-Model had a
confirmed one; the currently configured model
(prithivMLmods/deepfake-detector-model-v1) documents an explicit,
unambiguous mapping and has no such issue reported, but this script is
kept as a general safety net worth re-running any time IMAGE_MODEL_ID
changes in services/model_loader.py, rather than trusting a new model's
label text blindly.

Usage
-----
    cd backend
    python scripts/check_image_label_mapping.py path/to/real_photo.jpg path/to/ai_generated_photo.jpg

What to do with the result
---------------------------
- If it prints "Mapping looks correct" -> you're done, no changes needed.
- If it prints "Mapping looks INVERTED" -> set the environment variable
  before starting the backend:

      export IMAGE_REAL_LABEL_INDEX=<the index the script recommends>

  (On Windows: `set IMAGE_REAL_LABEL_INDEX=<index>`)

  services/image_detector.py reads this override before falling back to
  the (possibly-buggy) label text, so this fixes image AND video
  detection in one step (video reuses the same image model per frame).
"""

import sys

sys.path.insert(0, ".")  # allow running from backend/ without installing as a package

from services.model_loader import get_image_model, DEVICE  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402


def predict_raw(path):
    model, processor = get_image_model()
    image = Image.open(path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1).squeeze()
    return probs.tolist()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    real_path, fake_path = sys.argv[1], sys.argv[2]

    model, _ = get_image_model()
    id2label = model.config.id2label
    print(f"Model reports these labels: {id2label}\n")

    real_probs = predict_raw(real_path)
    fake_probs = predict_raw(fake_path)

    print(f"Known-REAL photo  ({real_path}):")
    for idx, p in enumerate(real_probs):
        print(f"  index {idx} ({id2label[idx]!r}): {p:.4f}")

    print(f"\nKnown-FAKE photo  ({fake_path}):")
    for idx, p in enumerate(fake_probs):
        print(f"  index {idx} ({id2label[idx]!r}): {p:.4f}")

    # Whichever index scores consistently HIGHER on the real photo and
    # LOWER on the fake photo is the true "real" index, regardless of
    # what its text label claims.
    real_argmax = max(range(len(real_probs)), key=lambda i: real_probs[i])
    fake_argmax = max(range(len(fake_probs)), key=lambda i: fake_probs[i])

    print(f"\nKnown-real photo scored highest on index {real_argmax} ({id2label[real_argmax]!r})")
    print(f"Known-fake photo scored highest on index {fake_argmax} ({id2label[fake_argmax]!r})")

    if real_argmax != fake_argmax and real_argmax not in (None,):
        true_real_index = real_argmax
        label_says = id2label[true_real_index].lower()
        text_agrees = "real" in label_says or "authentic" in label_says
        if text_agrees:
            print(
                f"\n✅ Mapping looks correct. Index {true_real_index} means 'real' "
                "and its label text agrees. No override needed."
            )
        else:
            print(
                f"\n⚠️  Mapping looks INVERTED. Index {true_real_index} is actually "
                f"'real' but its label text says {id2label[true_real_index]!r}.\n"
                f"Set this before starting the backend:\n\n"
                f"    export IMAGE_REAL_LABEL_INDEX={true_real_index}\n"
            )
    else:
        print(
            "\n❓ Inconclusive — both photos scored highest on the same index. "
            "Try a clearer / more typical example of each, or the model may "
            "just be performing poorly on these particular inputs."
        )


if __name__ == "__main__":
    main()
