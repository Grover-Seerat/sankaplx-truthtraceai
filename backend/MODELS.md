# TruthTrace AI — Forensic Model Architecture

## Core synthetic-image detector ensemble

TruthTrace uses three independent image-level synthetic-content detectors. The ensemble is designed for **content-agnostic** evidence rather than face-only deepfake detection.

### 1. Community Forensics 384 — Primary (50%)
- Checkpoint: `OwensLab/commfor-model-384`
- ViT-Small, 384×384 input.
- Trained as part of the Community Forensics work covering thousands of generators. The released Community Forensics dataset contains about 2.7M generated images from 4,803 generator models.
- Strong choice for cross-generator generalization.
- This is the primary synthetic-image signal.

### 2. Organika SDXL Detector — Secondary (30%)
- Checkpoint: `Organika/sdxl-detector`
- Standard Hugging Face image-classification checkpoint.
- Provides an independent semantic/image-level opinion, especially useful for SDXL-like synthetic imagery.
- Used as a secondary detector rather than the sole authority.

### 3. SteganographIA Detector — Tertiary / real-photo safeguard (20%)
- Checkpoint: `delpot/steganograph-ia-detector`
- ViT-B/16, 224×224 input, labels explicitly `real` and `ai_generated`.
- Trained on the Defactify dataset and evaluated on 15,000 balanced images. Its model card reports a 1.4% false-positive rate on real images, making it useful as a conservative counter-signal for genuine photographs.
- Its lower AI recall means it is intentionally not given the largest weight.

## Why this architecture

The three models provide different failure modes rather than three copies of the same architecture:

**Community Forensics → broad cross-generator primary evidence**

**Organika → independent semantic detector**

**SteganographIA → conservative real-photo safeguard**

The final synthetic score is a weighted ensemble:

`0.50 × Community Forensics + 0.30 × Organika + 0.20 × SteganographIA`

Weights are engineering priors, **not calibrated probabilities**. A production deployment should calibrate them on a held-out dataset containing original phone photos, WhatsApp-transcoded photos, AI images from multiple generators, and AI images after WhatsApp-style re-encoding.

## WhatsApp / social-media robustness

The system does not assume that JPEG compression means AI or that missing EXIF means AI. Transcoding, metadata, ELA, noise residuals and quantization are supporting forensic signals only. The detector ensemble still runs on the image itself.

The Reju983 frequency-aware architecture (SwinV2 + SRM + DCT + FFT) was considered as a candidate because its training description includes JPEG/downscale/blur augmentation. However, its public repository currently exposes the architecture and inference code but not a trained `model_state_dict.pt`; the inference script itself falls back to random initialization when those weights are absent. Therefore it is **not wired into the production verdict**, because a random-weight detector would be invalid.

## Other forensic modules

The ensemble is complemented by: SHA-256/MD5 and perceptual hashes, EXIF/file metadata, JPEG quantization, C2PA verification when available, ELA, noise residual statistics, OCR, optional CLIP claim alignment, GeoCLIP and temporal metadata consistency. None of these is treated as proof of authenticity by itself.

## Important limitation

TruthTrace reports evidence-based classifications such as **AI-Generated, Likely Authentic, Manipulated, or Inconclusive**. It does not claim mathematical proof that an image is real or AI-generated.
