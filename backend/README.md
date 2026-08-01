# Truelens Forensics API

FastAPI backend for the Truelens digital media forensics platform. Serves
three inference endpoints backed by real pretrained models — no training,
no fine-tuning, inference only, per the hackathon spec.

## Models used — hybrid routing

| Media | Model | Used when | Source |
|---|---|---|---|
| Image (face) | `prithivMLmods/deepfake-detector-model-v1` (SigLIP2) | A face is detected | Hugging Face Hub |
| Image (non-face) | `umm-maybe/AI-image-detector` (ConvNeXT) | No face detected — landscapes, art, animals, buildings, screenshots, products, etc. | Hugging Face Hub |
| Video | Both of the above, chosen per-frame, on scene-change-filtered frames | — | — |
| Audio | `garystafford/wav2vec2-deepfake-voice-detector` (Wav2Vec2), run on overlapping windows after VAD/denoise/normalize | — | Hugging Face Hub |

The backend decides which detector to use automatically — the user never
picks one. `services/image_detector.route_and_predict_frame()` is the
single routing function shared by the image and video pipelines: it runs
`utils/face_detection.py` (MediaPipe, Haar-cascade fallback) and sends the
result to the face model or the general model accordingly.

Models download automatically on first run (cached by `transformers` under
`~/.cache/huggingface`) and are loaded once at process startup — see
`services/model_loader.py`. They are **not** reloaded per-request. If the
general (non-face) model fails to load (offline dev, model renamed
upstream, etc.), the app **does not crash** — it logs a warning, disables
just that pipeline, and falls back to the face model on the full frame
with a `warnings` entry in the API response explaining the degradation.

## What's new in this pass (hybrid upgrade)

- **`utils/image_quality.py`** — blur (Laplacian variance), brightness,
  contrast, resolution, and a composite 0-100 quality score. Rejects
  corrupted/too-tiny/unusably-blurry uploads (HTTP 422) before running
  any model; non-fatal issues are attached to `warnings` instead. Also
  provides `enhance_contrast()` (CLAHE), applied to each face crop before
  inference.
- **`utils/face_detection.py`** — now detects *every* face (not just the
  largest), via MediaPipe with an automatic Haar-cascade fallback.
- **`services/general_image_detector.py`** — the non-face AI-image model
  described above, with the same "resolve which label index means real"
  safety pattern as the face detector.
- **`services/gradcam.py`** — Grad-CAM-style explainability for ViT/SigLIP2
  -family (patch-token) architectures: hooks the last transformer block,
  backprops the predicted class, and produces a heatmap + overlay as
  base64 PNGs. Degrades gracefully (returns `None`) for unsupported
  architectures rather than erroring the whole request.
- **`services/image_detector.py`** — now the orchestrator: quality gate →
  face detect → route to face-model-per-face (aggregated by the *most
  suspicious* face, not averaged) or general-model → Grad-CAM →
  human-readable explanation string.
- **`services/video_detector.py`** — replaced fixed 1-fps sampling with
  candidate sampling + histogram-based duplicate-frame filtering +
  blur-based frame skipping, then routes every kept frame through the
  same hybrid logic as a standalone image. Reports `frames_skipped`,
  `suspicious_timestamps`, and a richer per-frame timeline.
- **`services/audio_detector.py`** + **`utils/audio_dsp.py`** — voice-
  activity detection/silence trimming, Wiener-filter noise reduction, RMS
  loudness normalization, then inference on overlapping 4s/2s-hop windows
  instead of one pass over the raw clip, so a short synthetic splice in a
  long genuine recording isn't averaged away.
- **`utils/trust_score.py`** — `confidence` is now a distinct, calibrated
  number (not just distance-from-50%): it discounts the model's raw
  certainty by input quality (blur/brightness/contrast for images, valid-
  frame ratio for video, voiced-ratio/RMS for audio).
- **`routers/*.py`** — all three now return the new fields (`quality_score`,
  `blur_score`, `pipeline_used`, `heatmap`/`heatmap_overlay`, `warnings`,
  `confidence`, `frames_skipped`, `suspicious_timestamps`, `segments`,
  `suspicious_segments`, `faces`) **in addition to** every field that was
  already there — nothing existing was removed or renamed, so the
  frontend's original code paths keep working unmodified.

### New dependencies

Added to `requirements.txt`: `mediapipe` (multi-face detection) and
`scipy` (heatmap resizing + Wiener audio filter). Everything else reuses
what was already pinned. Run `pip install -r requirements.txt` again after
pulling this update.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

First run will download ~1-2GB of model weights, so make sure you're on a
decent connection before a live demo — consider running it once ahead of
time to warm the Hugging Face cache.

## Run

```bash
uvicorn app:app --reload --port 8000
```

The Vite frontend's dev server already proxies `/api/*` to
`http://localhost:8000` (see `frontend/vite.config.js`), so no extra CORS
config is needed for local dev beyond what's in `app.py`.

## Endpoints

- `GET  /api/health` — liveness check
- `POST /api/image/analyze` — multipart form, field `file` (jpg/png/webp, ≤25MB)
- `POST /api/video/analyze` — multipart form, field `file` (mp4/mov, ≤200MB)
- `POST /api/audio/analyze` — multipart form, field `file` (wav/mp3, ≤50MB)

All three return the same core JSON shape. Note there is a single headline
metric, `deepfake_probability` (0-100, higher = more likely AI-generated)
— there used to be two overlapping numbers (`trust_score` + `confidence`),
collapsed into one per product decision:

```json
{
  "prediction": "Likely Manipulated",
  "deepfake_probability": 82.4,
  "risk_level": "High",
  "media_type": "Image",
  "processing_time": "1.8 sec",
  "file_name": "example.jpg",
  "timestamp": "2026-07-31T12:00:00+00:00",
  "face_detected": true,
  "face_count": 1,
  "summary": "...",
  "visual_indicators": [{ "label": "...", "heuristic": true, "flagged": false }],
  "potential_manipulation_indicators": ["..."],
  "recommendations": ["..."]
}
```

Tiers: `0-20` Likely Authentic / Low risk, `21-50` Needs Manual
Verification / Medium risk, `51-100` Likely Manipulated / High risk.

`image/analyze` and `video/analyze` additionally return `face_detected`
(and `video` returns `face_detected_ratio`, the fraction of sampled
frames a face was found in). When no face is detected, the indicator
checklist and summary switch to whole-frame-only language instead of
listing face-specific checks (blink rate, facial boundary blending, etc)
that wouldn't mean anything for that input — see "Face detection" below.

`video/analyze` also returns `frame_analysis.timeline`, a per-second array
of `{ second, prob_real }` (raw model output) used for the frame-by-frame
breakdown chart on the frontend.

## Face detection & cropping

`utils/face_detection.py` runs OpenCV's bundled Haar cascade on every
image and every sampled video frame before it reaches the model
(`services/image_detector.py` -> `predict_frame_bgr`, reused by
`services/video_detector.py`). Two reasons this exists:

1. **Accuracy.** The image model was fine-tuned on cropped, aligned face
   datasets typical of deepfake benchmarks. Feeding it a whole uncropped
   photo is a distribution shift it handles badly. When a face is found,
   the model runs on a padded crop around the largest detected face
   instead of the full frame — closer to what it actually saw in
   training.
2. **Honest reporting.** If no face is present, `face_detected: false` is
   returned and `utils/report_text.py` swaps the indicator pool and
   summary text to whole-frame language, instead of listing face-specific
   reasoning (eye movement, blink rate, facial boundary blending) for
   media that has no face in it.

This is a fast Haar-cascade gate, not a research-grade face detector — it
can still miss faces at extreme angles, poor lighting, or very small in
frame. If that turns out to matter for your test set, swapping in a
stronger detector (e.g. a lightweight DNN-based one) is a drop-in
replacement inside `face_detection.py` without touching the callers.

## Structure

```
backend/
  app.py                  FastAPI app, CORS, router registration, startup hook
  routers/                One router per media type — thin HTTP layer only
  services/
    model_loader.py       Singleton model loading
    image_detector.py     ViT inference + face-crop, shared frame predictor
    video_detector.py     OpenCV frame sampling + image model reuse
    audio_detector.py     Wav2Vec2 inference
  utils/
    file_validation.py    Content-type / size checks per media type
    face_detection.py     Haar-cascade face detect + crop
    trust_score.py        prob_real -> prediction/deepfake_probability/risk_level
    report_text.py        Face-aware summary / indicators / recommendations copy
  scripts/
    check_image_label_mapping.py   One-off label-direction diagnostic (see below)
  uploads/, reports/       Scratch dirs (gitignored contents)
```

## Troubleshooting: poor or inverted image/video detection

If real photos come back "fake", fake photos also come back "fake", or
results otherwise look random/biased toward one verdict:

**1. Label mapping (unlikely with the current model, but check anyway).**
The previously-used `Deep-Fake-Detector-v2-Model` had a confirmed,
author-acknowledged bug where its `config.json` `id2label` didn't match
how it was actually trained. The currently configured model,
`prithivMLmods/deepfake-detector-model-v1`, documents an explicit,
unambiguous mapping (`{"0": "fake", "1": "real"}`) in its own model card
and has no such issue reported — but if you ever swap `IMAGE_MODEL_ID`
in `services/model_loader.py` for a different checkpoint, re-run this
diagnostic before trusting it, since this class of bug isn't unique to
any one model:

```bash
cd backend
python scripts/check_image_label_mapping.py path/to/real_photo.jpg path/to/ai_generated_photo.jpg
```

It tells you directly which raw index is actually "real" regardless of
label text, and if the label text is wrong, gives you the exact line to
set:

```bash
export IMAGE_REAL_LABEL_INDEX=<index it recommends>
```

This fixes both image and video detection in one step, since video reuses
this same model per sampled frame.

**2. Face-crop distribution shift.** Handled automatically (see "Face
detection & cropping" above) — the model runs on a face crop when one is
found, not the whole frame. If detection is still weak after confirming
the label mapping is correct, the remaining lever is the model itself:
this is one publicly available deepfake-detector checkpoint (reported
~94.4% accuracy on its own eval set, per its model card), not a
research-grade ensemble, and its ceiling on your specific real-world test
images may differ from that benchmark number. Swapping `IMAGE_MODEL_ID`
in `services/model_loader.py` for a different Hugging Face checkpoint is a
contained change if you want to try an alternative.

## Notes / next steps

- The "visual indicators" checklist is derived from the model's single
  authenticity score plus the face-detection result, not independently
  measured per indicator — the API labels every indicator
  `heuristic: true` for this reason. A stretch goal would be wiring in
  real per-indicator signals (e.g. an actual face-landmark consistency
  check via OpenCV/dlib) instead of a heuristically-flagged checklist.
- Face detection uses a fast Haar cascade, not a research-grade detector
  — see "Face detection & cropping" above for its limits.
- Project scope is real-time analysis only — no PDF export, no separate
  detection-history page. The dashboard's "Deepfake probability history" /
  "Risk distribution" charts are in-session only, backed by the
  frontend's `localStorage` (see `frontend/src/lib/detectionHistory.js`);
  there's no server-side persistence and none is planned for this scope.
